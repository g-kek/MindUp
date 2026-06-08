from __future__ import annotations

import asyncio
import json
import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from mindup_bot.ai.gemini_retry import call_with_model_fallback, model_candidates
from mindup_bot.config import Settings

ModelT = TypeVar("ModelT", bound=BaseModel)


class GeminiGateway:
    def __init__(self, settings: Settings) -> None:
        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
        self._models = model_candidates(settings.gemini_model, settings.gemini_fallback_models)
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        schema: type[ModelT],
        temperature: float = 0.4,
    ) -> ModelT:
        return await asyncio.to_thread(
            self._generate_json_sync,
            system_instruction,
            prompt,
            schema,
            temperature,
        )

    def _generate_json_sync(
        self,
        system_instruction: str,
        prompt: str,
        schema: type[ModelT],
        temperature: float,
    ) -> ModelT:
        response = call_with_model_fallback(
            self._models,
            lambda model: self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                ),
            ),
            operation="generate_content",
        )
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        if parsed is not None:
            return schema.model_validate(parsed)
        return parse_json_model(response.text or "{}", schema)


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
