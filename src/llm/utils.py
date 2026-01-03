"""Shared utilities for LLM provider and model configuration."""

from src.config import settings


def _is_valid_api_key(key: str | None) -> bool:
    """Check if API key is valid (not None, not empty, not a placeholder)."""
    if not key:
        return False
    placeholder_patterns = ["your_", "_here", "sk-xxx", "placeholder"]
    return not any(p in key.lower() for p in placeholder_patterns)


def format_model_name(model: str) -> str:
    """Format model name with proper provider prefix for LiteLLM.

    Args:
        model: Model name, optionally with provider prefix

    Returns:
        Model name with appropriate provider prefix for LiteLLM
    """
    # If model already has a provider prefix, return as-is
    if "/" in model:
        return model

    # Check explicit provider setting (except default openai)
    provider = settings.default_llm_provider.lower()
    if provider and provider != "openai":
        mapping = {
            "deepseek": "deepseek",
            "openrouter": "openrouter",
            "anthropic": "anthropic",
        }
        prefix = mapping.get(provider, provider)
        return f"{prefix}/{model}"

    # Auto-detect provider based on available API keys and model patterns
    if settings.openai_api_key and (model.startswith("gpt-") or model.startswith("text-")):
        return f"openai/{model}"

    if settings.deepseek_api_key and model.startswith("deepseek-"):
        return f"deepseek/{model}"

    if settings.anthropic_api_key and "claude" in model:
        return f"anthropic/{model}"

    if settings.openrouter_api_key:
        # Fallback for OpenRouter if we have the key but no clear pattern
        return f"openrouter/{model}"

    # Fallback to generic OpenAI if API base is set
    if settings.llm_api_base:
        return f"openai/{model}"

    return model


def get_api_key_for_model(model: str) -> str | None:
    """Get the appropriate API key based on model prefix.

    Args:
        model: Model name with provider prefix (e.g., "deepseek/deepseek-chat")

    Returns:
        API key for the provider, or None if not available
    """
    if "/" not in model:
        # No prefix, try to find any valid key
        if _is_valid_api_key(settings.openai_api_key):
            return settings.openai_api_key
        if _is_valid_api_key(settings.anthropic_api_key):
            return settings.anthropic_api_key
        if _is_valid_api_key(settings.deepseek_api_key):
            return settings.deepseek_api_key
        if _is_valid_api_key(settings.openrouter_api_key):
            return settings.openrouter_api_key
        return None

    provider = model.split("/")[0].lower()

    key_map = {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "deepseek": settings.deepseek_api_key,
        "openrouter": settings.openrouter_api_key,
    }

    key = key_map.get(provider)
    if _is_valid_api_key(key):
        return key

    # Fallback: try other valid keys
    for fallback_key in [settings.openrouter_api_key, settings.deepseek_api_key,
                         settings.anthropic_api_key, settings.openai_api_key]:
        if _is_valid_api_key(fallback_key):
            return fallback_key

    return None
