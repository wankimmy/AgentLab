import asyncio

import pytest

from app.providers.base import ChatRequest
from app.providers.mock import MockProvider


def test_mock_provider_deterministic():
    provider = MockProvider()
    messages = [{"role": "user", "content": "Hello world"}]
    r1 = asyncio.run(provider.complete(ChatRequest(model="mock-model", messages=messages)))
    r2 = asyncio.run(provider.complete(ChatRequest(model="mock-model", messages=messages)))
    assert r1.content == r2.content
    assert "[mock:" in r1.content


@pytest.mark.asyncio
async def test_mock_provider_stream():
    provider = MockProvider()
    messages = [{"role": "user", "content": "Hello stream"}]
    events = []
    async for event in provider.stream(ChatRequest(model="mock-model", messages=messages)):
        events.append(event)
    assert any(e.type == "token" for e in events)
    done = next(e for e in events if e.type == "done")
    assert done.input_tokens >= 0
    assert done.output_tokens >= 0
