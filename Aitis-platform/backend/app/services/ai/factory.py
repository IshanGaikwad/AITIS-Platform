from typing import Optional

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.mock_provider import MockAIProvider


class AIProviderFactory:
    """
    Factory to manage AI provider instantiation based on configuration.
    Ensures the platform remains vendor-neutral.
    """

    _instance: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """
    Returns the configured AI provider.

    Uses the real Groq provider when an API key is configured (settings.ai_enabled),
    otherwise falls back to the deterministic MockAIProvider so the platform still
    runs without any LLM credentials.
    """
    if AIProviderFactory._instance is None:
        if settings.ai_enabled:
            # Imported lazily so the openai dependency is only loaded when used
            from app.services.ai.groq_provider import GroqProvider

            AIProviderFactory._instance = GroqProvider()
        else:
            AIProviderFactory._instance = MockAIProvider()

    return AIProviderFactory._instance
