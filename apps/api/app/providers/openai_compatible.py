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

    def _build_payload(self, request: ChatRequest, *, stream: bool) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

        if request.tools:
            payload["tools"] = request.tools

            payload["tool_choice"] = "auto"

        return payload

    async def complete(self, request: ChatRequest) -> ChatResponse:
        payload = self._build_payload(request, stream=False)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

        message = data["choices"][0]["message"]

        tool_calls = message.get("tool_calls")

        if tool_calls:
            return ChatResponse(
                content="",
                input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=data.get("usage", {}).get("completion_tokens", 0),
            )

        usage = data.get("usage", {})

        return ChatResponse(
            content=message.get("content") or "",
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        payload = self._build_payload(request, stream=True)

        full_content: list[str] = []

        input_tokens = 0

        output_tokens = 0

        tool_calls_acc: dict[int, dict] = {}

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

                        choice = chunk.get("choices", [{}])[0]

                        delta = choice.get("delta", {})

                        text = delta.get("content")

                        if text:
                            full_content.append(text)

                            yield StreamEvent(type="token", content=text)

                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)

                            entry = tool_calls_acc.setdefault(
                                idx,
                                {"id": "", "name": "", "arguments": ""},
                            )

                            if tc.get("id"):
                                entry["id"] = tc["id"]

                            fn = tc.get("function") or {}

                            if fn.get("name"):
                                entry["name"] = fn["name"]

                            if fn.get("arguments"):
                                entry["arguments"] += fn["arguments"]

                        finish = choice.get("finish_reason")

                        if finish == "tool_calls" and tool_calls_acc:
                            parsed = []

                            for entry in tool_calls_acc.values():
                                parsed.append(
                                    {
                                        "id": entry["id"],
                                        "name": entry["name"],
                                        "arguments": json.loads(entry["arguments"] or "{}"),
                                    }
                                )

                            yield StreamEvent(type="tool_calls", metadata={"tool_calls": parsed})

                            return

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
