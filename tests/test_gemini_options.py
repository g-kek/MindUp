from unittest.mock import MagicMock

from google.genai import types

from mindup_bot.ai.gemini import GeminiGateway, model_generation_options
from mindup_bot.ai.schemas import TranslationResult


def test_gemini4_uses_thinking_level_without_sampling_parameters():
    config = types.GenerateContentConfig(
        **model_generation_options("models/gemini-4-hydrogen", "medium", 0.35),
    )
    assert config.temperature is None
    assert config.top_p is None and config.top_k is None
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MEDIUM


def test_generation_options_remain_compatible_with_older_overrides():
    flash = types.GenerateContentConfig(
        **model_generation_options("gemini-3.8-flash", "low", 0.2),
    )
    assert flash.temperature == 0.2
    assert flash.thinking_config.thinking_level == types.ThinkingLevel.LOW
    legacy = types.GenerateContentConfig(
        **model_generation_options("gemini-2.5-flash", "medium", 0.2),
    )
    assert legacy.temperature == 0.2
    assert legacy.thinking_config is None


def test_fallback_receives_its_own_model_specific_generation_config():
    from google.genai import errors

    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway._models = ["gemini-4-hydrogen", "gemini-3.8-flash"]
    gateway._thinking_level = "medium"
    gateway._client = MagicMock()
    gateway._client.models.generate_content.side_effect = [
        errors.ServerError(
            503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "busy"}}
        ),
        MagicMock(parsed=TranslationResult(translation="Hello")),
    ]
    result = gateway._generate_json_sync("Translate", "Привет", TranslationResult, 0.2)
    assert result.translation == "Hello"
    configs = [
        call.kwargs["config"] for call in gateway._client.models.generate_content.call_args_list
    ]
    assert configs[0].temperature is None
    assert configs[1].temperature == 0.2
    assert configs[1].thinking_config.thinking_level == types.ThinkingLevel.MEDIUM
