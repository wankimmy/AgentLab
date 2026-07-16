from app.providers.mock import MockProvider


def test_mock_provider_deterministic():
    provider = MockProvider()
    messages = [{"role": "user", "content": "Hello world"}]
    r1 = provider.complete(messages)
    r2 = provider.complete(messages)
    assert r1.content == r2.content
    assert "[mock:" in r1.content
