import pytest
from google.genai import errors

from mindup_bot.ai.gemini_retry import (
    TransientGeminiError,
    call_with_model_fallback,
    model_candidates,
)


def test_model_candidates_deduplicates_and_strips_models() -> None:
    assert model_candidates(
        "gemini-2.5-flash",
        " gemini-2.5-flash-lite, gemini-2.5-flash-lite, ",
    ) == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def test_call_with_model_fallback_uses_next_model_after_503() -> None:
    calls: list[str] = []

    def call(model: str) -> str:
        calls.append(model)
        if model == "primary":
            raise _server_error(503)
        return f"ok:{model}"

    result = call_with_model_fallback(["primary", "fallback"], call, operation="test")

    assert result == "ok:fallback"
    assert calls == ["primary", "fallback"]


def test_call_with_model_fallback_raises_when_all_models_are_transiently_unavailable() -> None:
    with pytest.raises(TransientGeminiError):
        call_with_model_fallback(
            ["primary", "fallback"],
            lambda _model: (_ for _ in ()).throw(_server_error(503)),
            operation="test",
        )


def test_call_with_model_fallback_does_not_hide_client_errors() -> None:
    with pytest.raises(errors.ClientError):
        call_with_model_fallback(
            ["primary", "fallback"],
            lambda _model: (_ for _ in ()).throw(_client_error(400)),
            operation="test",
        )


def _server_error(code: int) -> errors.ServerError:
    return errors.ServerError(
        code,
        {"error": {"code": code, "status": "UNAVAILABLE", "message": "busy"}},
    )


def _client_error(code: int) -> errors.ClientError:
    return errors.ClientError(
        code,
        {"error": {"code": code, "status": "INVALID_ARGUMENT", "message": "bad request"}},
    )
