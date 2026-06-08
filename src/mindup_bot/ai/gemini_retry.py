from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from google.genai import errors

logger = logging.getLogger(__name__)

ResultT = TypeVar("ResultT")

_TRANSIENT_STATUS_CODES = {500, 503, 504}


class TransientGeminiError(RuntimeError):
    """Raised when Gemini stays unavailable after configured fallbacks."""


def model_candidates(primary_model: str, fallback_models: str) -> list[str]:
    models: list[str] = []
    for model in (primary_model, *fallback_models.split(",")):
        model = model.strip()
        if model and model not in models:
            models.append(model)
    return models


def call_with_model_fallback(
    models: list[str],
    call: Callable[[str], ResultT],
    *,
    operation: str,
) -> ResultT:
    if not models:
        raise ValueError("At least one Gemini model must be configured")

    last_error: errors.APIError | None = None
    for model in models:
        try:
            return call(model)
        except errors.APIError as exc:
            if not is_transient_gemini_error(exc):
                raise
            last_error = exc
            logger.warning(
                "Gemini %s failed on model %s with transient error %s %s",
                operation,
                model,
                getattr(exc, "code", "unknown"),
                getattr(exc, "status", "unknown"),
            )

    raise TransientGeminiError(
        f"Gemini {operation} is temporarily unavailable for configured models: "
        f"{', '.join(models)}"
    ) from last_error


def is_transient_gemini_error(exc: BaseException) -> bool:
    if isinstance(exc, errors.ServerError):
        return True
    if isinstance(exc, errors.APIError):
        return int(getattr(exc, "code", 0) or 0) in _TRANSIENT_STATUS_CODES
    return False
