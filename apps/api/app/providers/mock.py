import hashlib
from dataclasses import dataclass


@dataclass
class ChatResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0


class MockProvider:
    """Deterministic mock provider for CI and local development."""

    def complete(self, messages: list[dict], model: str = "mock-model") -> ChatResponse:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        digest = hashlib.sha256(last_user.encode()).hexdigest()[:8]
        content = f"[mock:{model}] Response for: {last_user[:80]} (id={digest})"
        return ChatResponse(
            content=content,
            input_tokens=len(last_user.split()),
            output_tokens=len(content.split()),
        )
