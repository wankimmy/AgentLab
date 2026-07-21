from app.core.config import settings
from app.providers.mock import MockProvider
from app.providers.mock_judge import MockJudgeProvider
from app.providers.openai_compatible import OpenAICompatibleProvider

ProviderType = MockProvider | OpenAICompatibleProvider
JudgeProviderType = MockJudgeProvider | OpenAICompatibleProvider


def get_provider(provider_name: str) -> ProviderType:
    if provider_name == "mock":
        return MockProvider()
    if settings.ai_api_key:
        return OpenAICompatibleProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
        )
    return MockProvider()


def get_judge_provider() -> JudgeProviderType:
    if settings.judge_api_key:
        return OpenAICompatibleProvider(
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
        )
    return MockJudgeProvider()
