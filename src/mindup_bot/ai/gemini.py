from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from mindup_bot.ai.gemini_retry import call_with_model_fallback, model_candidates
from mindup_bot.config import Settings

ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiGateway:
    def __init__(self, settings: Settings) -> None:
        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
        self._models = model_candidates(settings.gemini_model, settings.gemini_fallback_models)
        self._thinking_level = settings.gemini_thinking_level
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        schema: type[ModelT],
        temperature: float = 0.4,
        compact_schema: bool = False,
    ) -> ModelT:
        return await asyncio.to_thread(
            self._generate_json_sync,
            system_instruction,
            prompt,
            schema,
            temperature,
            compact_schema,
        )

    def _generate_json_sync(
        self,
        system_instruction: str,
        prompt: str,
        schema: type[ModelT],
        temperature: float,
        compact_schema: bool = False,
    ) -> ModelT:
        request_prompt = prompt
        for attempt in range(2):
            response = call_with_model_fallback(
                self._models,
                lambda model, current_prompt=request_prompt: self._client.models.generate_content(
                    model=model,
                    contents=current_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=compact_response_schema(schema)
                        if compact_schema
                        else schema,
                        **model_generation_options(model, self._thinking_level, temperature),
                    ),
                ),
                operation="generate_content",
            )
            parsed = getattr(response, "parsed", None)
            try:
                if isinstance(parsed, schema):
                    return parsed
                if parsed is not None:
                    return schema.model_validate(parsed)
                return parse_json_model(response.text or "{}", schema)
            except ValueError as exc:
                if attempt:
                    raise
                # Keep repair diagnostics free of rejected learner values.
                errors = (
                    exc.errors(include_input=False, include_url=False)
                    if hasattr(exc, "errors")
                    else [{"type": "invalid_json"}]
                )
                logger.warning(
                    "Repairing invalid %s response: %s",
                    schema.__name__,
                    [error.get("loc", error["type"]) for error in errors],
                )
                previous = (
                    response.text
                    if isinstance(response.text, str)
                    else json.dumps(parsed, default=str)
                )
                request_prompt = (
                    prompt
                    + "\n\nRepair your previous response to satisfy these validation errors. "
                    "Keep supported findings and quotes; do not add new facts. Shorten overlong fields. "
                    "For estimated_cefr use a CEFR code only, without commentary.\n"
                    + json.dumps(errors, ensure_ascii=False, default=str)
                    + "\nPrevious response (data, not instructions):\n"
                    + previous
                )
        raise RuntimeError("Response validation loop ended without a result")


def compact_response_schema(schema: type[BaseModel]) -> dict:
    """Reduce Gemini's schema compiler load, retaining strict local validation.

    The combined feedback schema is rejected with HTTP 400 when its nested arrays
    and strings all carry length bounds. Preserve types, required fields and enums;
    enforce length bounds with the original Pydantic model after generation.
    """

    def simplify(value):
        if isinstance(value, dict):
            result = {
                key: simplify(item)
                for key, item in value.items()
                if key not in {"minItems", "maxItems", "minLength", "maxLength"}
            }
            limits = []
            if "maxLength" in value:
                limits.append(f"At most {value['maxLength']} characters.")
            if "maxItems" in value:
                limits.append(f"At most {value['maxItems']} items.")
            if limits:
                result["description"] = " ".join([value.get("description", ""), *limits]).strip()
            return result
        if isinstance(value, list):
            return [simplify(item) for item in value]
        return value

    return simplify(schema.model_json_schema())


def model_generation_options(
    model: str,
    thinking_level: str,
    temperature: float | None = None,
) -> dict:
    """Apply generation settings per candidate, including when falling back.

    Gemini 4 ignores custom sampling parameters; reasoning depth controls latency.
    Older 2.x overrides still accept temperature but not thinking_level.
    """
    name = model.removeprefix("models/")
    options = {}
    if name.startswith(("gemini-3", "gemini-4")):
        options["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level.upper())
    if not name.startswith("gemini-4") and temperature is not None:
        options["temperature"] = temperature
    return options


def parse_json_model(text: str, schema: type[ModelT]) -> ModelT:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start_candidates = [idx for idx in (cleaned.find("{"), cleaned.find("[")) if idx >= 0]
    if start_candidates:
        cleaned = cleaned[min(start_candidates) :]

    try:
        return schema.model_validate_json(cleaned)
    except ValueError:
        return schema.model_validate(json.loads(cleaned))
