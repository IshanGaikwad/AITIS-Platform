from typing import Optional, Type
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
    Defaults to MockAIProvider if no provider is configured or in development mode.
    """
    if AIProviderFactory._instance is None:
        # In a real implementation, this would check settings.ai_provider
        # and instantiate the corresponding class (e.g., OpenAIProvider, AnthropicProvider)
        
        # Defaulting to Mock for now as per Phase 3 requirements for deterministic testing
        AIProviderFactory._instance = MockAIProvider()
        
    return AIProviderFactory._instance
