import json

from app.judges.mock_payload import mock_judge_payload
from app.judges.rubrics import STANDARD_SIX_CRITERIA
from app.providers.base import ChatRequest, ChatResponse


class MockJudgeProvider:
    """Returns structured JSON judge scores for CI."""

    async def complete(self, request: ChatRequest) -> ChatResponse:
        user_msg = next(
            (m["content"] for m in reversed(request.messages) if m.get("role") == "user"), ""
        )
        assistant = ""
        if "Assistant answer:" in user_msg:
            assistant = user_msg.split("Assistant answer:", 1)[1].split("\n\n", 1)[0].strip()

        judge_index = None
        for m in request.messages:
            if m.get("role") == "system" and "judge #" in m.get("content", ""):
                try:
                    frag = m["content"].split("judge #")[1]
                    judge_index = int(frag.split(" ", 1)[0]) - 1
                except (IndexError, ValueError):
                    judge_index = None

        payload = mock_judge_payload(STANDARD_SIX_CRITERIA, assistant, judge_index)
        content = json.dumps(payload)
        return ChatResponse(content=content, input_tokens=100, output_tokens=80)

    def stream(self, request: ChatRequest):
        async def _gen():
            resp = await self.complete(request)
            yield type("E", (), {"type": "done", "content": resp.content})()

        return _gen()
