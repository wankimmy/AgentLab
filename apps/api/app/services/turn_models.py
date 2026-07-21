import hashlib
from dataclasses import dataclass

from app.models.entities import AgentVersion, Conversation, MessageRole

SUMMARY_RECENT_MESSAGES = 20


@dataclass
class TurnOverrides:
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    memory_mode: str | None = None


@dataclass
class StreamResult:
    event_type: str
    data: dict


def _memory_mode(version: AgentVersion, overrides: TurnOverrides | None) -> str:
    if overrides and overrides.memory_mode:
        return overrides.memory_mode
    return version.memory_config.get("mode", "conversation")


def assemble_messages(
    version: AgentVersion,
    conversation: Conversation,
    user_content: str,
    overrides: TurnOverrides | None,
) -> list[dict]:
    system_prompt = (
        overrides.system_prompt if overrides and overrides.system_prompt else version.system_prompt
    )
    mode = _memory_mode(version, overrides)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    prior = sorted(
        [m for m in conversation.messages if m.role != MessageRole.system],
        key=lambda m: m.sequence,
    )
    if mode == "none":
        messages.append({"role": "user", "content": user_content})
        return messages

    if mode == "summarised" and conversation.memory_summary:
        messages.append(
            {
                "role": "system",
                "content": f"Conversation summary:\n{conversation.memory_summary}",
            }
        )
        recent = prior[-SUMMARY_RECENT_MESSAGES:]
    else:
        recent = prior

    for msg in recent:
        messages.append({"role": msg.role.value, "content": msg.content})
    messages.append({"role": "user", "content": user_content})
    return messages


def regenerate_summary_stub(conversation: Conversation) -> str:
    texts = [
        m.content
        for m in conversation.messages
        if m.role in (MessageRole.user, MessageRole.assistant)
    ]
    combined = "\n".join(texts[-10:])
    digest = hashlib.sha256(combined.encode()).hexdigest()[:8]
    preview = combined[:400] + ("..." if len(combined) > 400 else "")
    return f"[summary:{digest}] {preview}"
