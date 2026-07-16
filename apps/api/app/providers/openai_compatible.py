import json
from collections.abc import AsyncGenerator

import httpx

from app.providers.base import ChatRequest, ChatResponse, StreamEvent


class OpenAICompatibleProvider:
    """OpenAI-compatible chat completions provider."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResponse(
            content=choice or "",
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        full_content: list[str] = []
        input_tokens = 0
        output_tokens = 0
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        chunk = json.loads(raw)
                        if "usage" in chunk and chunk["usage"]:
                            input_tokens = chunk["usage"].get("prompt_tokens", input_tokens)
                            output_tokens = chunk["usage"].get("completion_tokens", output_tokens)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content")
                        if text:
                            full_content.append(text)
                            yield StreamEvent(type="token", content=text)
        except httpx.HTTPStatusError as exc:
            yield StreamEvent(
                type="error",
                error_code=str(exc.response.status_code),
                error_message=exc.response.text[:200],
            )
            return
        except Exception as exc:
            yield StreamEvent(type="error", error_code="provider_error", error_message=str(exc))
            return

        yield StreamEvent(
            type="done",
            content="".join(full_content),
            input_tokens=input_tokens,
            output_tokens=output_tokens or len("".join(full_content).split()),
        )
