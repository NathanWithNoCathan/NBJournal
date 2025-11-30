"""Module for OpenAI prompter functionality."""

from openai import OpenAI
from DataClasses.settings import user_settings

openai_client = None
if user_settings.ai_settings.enabled and user_settings.ai_settings.api_key:
    openai_client = OpenAI(api_key=user_settings.ai_settings.api_key)

def sentiment_analysis_enabled() -> bool:
    """Check if sentiment analysis feature is enabled."""
    return user_settings.ai_settings.sentiment_analysis and user_settings.ai_settings.enabled and openai_client is not None

def tag_recommendations_enabled() -> bool:
    """Check if tag recommendations feature is enabled."""
    return user_settings.ai_settings.tag_recommendations and user_settings.ai_settings.enabled and openai_client is not None

def content_summarization_enabled() -> bool:
    """Check if content summarization feature is enabled."""
    return user_settings.ai_settings.content_summarization and user_settings.ai_settings.enabled and openai_client is not None

def send_prompt_to_openai(system: str, prompt: str, model: str = "gpt-5.1", *, json_mode: bool | None = None) -> dict:
    """Send a prompt to OpenAI and return the response.

    If ``json_mode`` is True, the call will request strictly
    structured JSON output using ``response_format={"type": "json_object"}``.
    If ``json_mode`` is False, a normal free-form text completion is
    requested. If ``json_mode`` is None, JSON mode is enabled by
    default because all current call sites expect JSON.
    """

    if openai_client is None:
        raise RuntimeError("OpenAI client is not initialized. Check AI settings and API key.")

    if json_mode is None:
        json_mode = True

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }

    if json_mode:
        # Force the model to return valid JSON.
        kwargs["response_format"] = {"type": "json_object"}

    response = openai_client.chat.completions.create(**kwargs)
    return response