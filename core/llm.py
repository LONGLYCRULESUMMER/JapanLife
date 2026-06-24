from __future__ import annotations

from langchain_deepseek import ChatDeepSeek

from core.config import settings


def get_llm(model: str | None = None, temperature: float = 0.0) -> ChatDeepSeek:
    """Build the DeepSeek chat model. Swap the provider here to change the whole app's LLM."""
    return ChatDeepSeek(
        model=model or settings.llm_model,
        api_key=settings.deepseek_api_key,
        temperature=temperature,
    )
