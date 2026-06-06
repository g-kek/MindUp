from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from mindup_bot.ai.gemini import GeminiGateway
from mindup_bot.ai.roles import Evaluator, MemoryUpdater, TopicSelector, Tutor
from mindup_bot.bot.handlers import register_handlers
from mindup_bot.bot.reminders import schedule_existing_reminders
from mindup_bot.config import get_settings
from mindup_bot.db import Database
from mindup_bot.services.speech import SpeechToText, TextToSpeech


async def post_init(application: Application) -> None:
    db: Database = application.bot_data["db"]
    settings = application.bot_data["settings"]
    await db.init()
    await schedule_existing_reminders(application, db, settings.app_timezone)


def build_application() -> Application:
    settings = get_settings()
    db = Database(settings.database_path)
    gemini = GeminiGateway(settings)

    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .concurrent_updates(False)
        .build()
    )
    application.bot_data.update(
        {
            "settings": settings,
            "db": db,
            "topic_selector": TopicSelector(gemini),
            "tutor": Tutor(gemini),
            "evaluator": Evaluator(gemini),
            "memory_updater": MemoryUpdater(gemini),
            "speech_to_text": SpeechToText(settings),
            "text_to_speech": TextToSpeech(settings),
        }
    )
    register_handlers(application)
    return application


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

