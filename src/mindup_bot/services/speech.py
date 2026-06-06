from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import edge_tts
from google import genai

from mindup_bot.config import Settings


class SpeechToText:
    def __init__(self, settings: Settings) -> None:
        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_stt_model

    async def transcribe(self, audio_path: Path) -> str:
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: Path) -> str:
        uploaded = self._client.files.upload(file=str(audio_path))
        prompt = """
Transcribe this Telegram voice message into English text.
If the speaker uses Russian or another language, translate the meaning into English.
Return only the transcript, no commentary.
""".strip()
        response = self._client.models.generate_content(
            model=self._model,
            contents=[prompt, uploaded],
        )
        return (response.text or "").strip()


class TextToSpeech:
    def __init__(self, settings: Settings) -> None:
        self._audio_dir = settings.audio_dir
        self._voice = settings.tts_voice
        self._rate = settings.tts_rate

    async def synthesize(self, text: str) -> Path:
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._audio_dir / f"tts-{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(text, voice=self._voice, rate=self._rate)
        await communicate.save(str(output_path))
        return output_path

