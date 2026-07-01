"""Groq LLM provider — uses the OpenAI-compatible Groq API.

Implements the vendor-neutral AIProvider interface so the rest of the platform
stays decoupled from the concrete LLM vendor.
"""

from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.ai.base import AIProvider, AIResponse


class GroqProvider(AIProvider):
    """AIProvider backed by Groq's OpenAI-compatible chat completions API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
        self._model = settings.ai_model

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AIResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
        )
        choice = resp.choices[0]
        return AIResponse(
            content=choice.message.content or "",
            confidence=0.9,
            model_name=self._model,
            provider="groq",
            tokens_used=resp.usage.total_tokens if resp.usage else None,
        )

    async def generate_structured_data(
        self,
        prompt: str,
        system_instruction: str,
        response_model: Any = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> AIResponse:
        """Generate a JSON response. Uses Groq JSON mode so the content is valid JSON."""
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
            response_format={"type": "json_object"},
        )
        choice = resp.choices[0]
        return AIResponse(
            content=choice.message.content or "{}",
            confidence=0.9,
            model_name=self._model,
            provider="groq",
            tokens_used=resp.usage.total_tokens if resp.usage else None,
        )
