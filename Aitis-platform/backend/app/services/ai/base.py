from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AIResponse(BaseModel):
    """Standardized response from any AI provider"""
    content: str
    confidence: float = Field(..., ge=0, le=1)
    model_name: str
    provider: str
    tokens_used: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AIProvider(ABC):
    """Abstract base class for AI providers to ensure vendor neutrality"""
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: str, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """Generate a text response based on a prompt and system instructions"""
        pass

    @abstractmethod
    async def generate_structured_data(
        self, 
        prompt: str, 
        system_instruction: str, 
        response_model: Any,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        """Generate a response that conforms to a specific Pydantic model"""
        pass
