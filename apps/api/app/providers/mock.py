import asyncio
import hashlib
from collections.abc import AsyncGenerator

from app.providers.base import ChatRequest, ChatResponse, StreamEvent


class MockProvider:
    """Deterministic mock provider for CI and local development."""

    def __init__(self, scenario: str | None = None) -> None:
        self.scenario = scenario

    def _build_content(self, messages: list[dict], model: str) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        digest = hashlib.sha256(last_user.encode()).hexdigest()[:8]
        return f"[mock:{model}] Response for: {last_user[:80]} (id={digest})"

    def _token_counts(self, messages: list[dict], content: str) -> tuple[int, int]:
        input_text = " ".join(m.get("content", "") for m in messages)
        return len(input_text.split()), len(content.split())

    async def complete(self, request: ChatRequest) -> ChatResponse:
        if self.scenario == "timeout":
            await asyncio.sleep(0.01)
            raise TimeoutError("Mock timeout scenario")
        if self.scenario == "rate_limit":
            raise RuntimeError("rate_limit")
        content = self._build_content(request.messages, request.model)
        in_tok, out_tok = self._token_counts(request.messages, content)
        return ChatResponse(content=content, input_tokens=in_tok, output_tokens=out_tok)

    async def stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        if self.scenario == "timeout":
            await asyncio.sleep(0.01)
            yield StreamEvent(type="error", error_code="timeout", error_message="Mock timeout")
            return
        if self.scenario == "rate_limit":
            yield StreamEvent(
                type="error", error_code="rate_limit", error_message="Mock rate limit"
            )
            return

        content = self._build_content(request.messages, request.model)
        in_tok, out_tok = self._token_counts(request.messages, content)
        words = content.split(" ")
        for i, word in enumerate(words):
            await asyncio.sleep(0)
            chunk = word if i == 0 else f" {word}"
            yield StreamEvent(type="token", content=chunk)
        yield StreamEvent(
            type="done",
            content=content,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
