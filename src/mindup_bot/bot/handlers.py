from __future__ import annotations

import logging
import uuid
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mindup_bot.ai.roles import Evaluator, MemoryUpdater, TopicSelector, Tutor
from mindup_bot.ai.schemas import Feedback, TopicChoice, TutorReply
from mindup_bot.bot.formatters import format_feedback, format_progress, format_settings
from mindup_bot.bot.keyboards import (
    CORRECTION_OPTIONS,
    GOAL_OPTIONS,
    LANGUAGE_OPTIONS,
    LEVEL_OPTIONS,
    REMINDER_OPTIONS,
    main_menu,
    option_keyboard,
    practice_reply_keyboard,
    topics_keyboard,
)
from mindup_bot.bot.reminders import schedule_user_reminder
from mindup_bot.config import Settings
from mindup_bot.db import Database
from mindup_bot.services.speech import SpeechToText, TextToSpeech

logger = logging.getLogger(__name__)

ONBOARDING_ORDER = [
    "english_level",
    "goal",
    "topics",
    "correction_style",
    "reminder_time",
    "interface_language",
]


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("finish", finish))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("subscription", subscription))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.VOICE | filters.TEXT, handle_practice_message))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if user["onboarding_completed"]:
        await update.effective_message.reply_text(
            "Welcome back. Choose what you want to do.",
            reply_markup=main_menu(user.get("interface_language")),
        )
        return

    await update.effective_message.reply_text(
        "Привет. Я помогу тебе каждый день 10 минут думать и говорить на английском.\n\n"
        "Сначала быстро настроим практику под тебя."
    )
    await ask_onboarding_step(update, context, "english_level", user.get("onboarding_data", {}))


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    await update.effective_message.reply_text(
        "Main menu",
        reply_markup=main_menu(user.get("interface_language")),
    )


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    db: Database = context.application.bot_data["db"]
    data = await db.get_progress(user["telegram_id"])
    await update.effective_message.reply_text(format_progress(data), reply_markup=main_menu())


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    await update.effective_message.reply_text(
        format_settings(user),
        reply_markup=main_menu(user.get("interface_language")),
    )


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    await update.effective_message.reply_text(
        "Subscription\n\nMVP mode: your first sessions are free. Payments are not enabled yet.",
        reply_markup=main_menu(),
    )


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    db: Database = context.application.bot_data["db"]
    session = await db.get_active_session(user["telegram_id"])
    if not session:
        await update.effective_message.reply_text("No active session.", reply_markup=main_menu())
        return
    await finish_session(update, context, user, session)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    user = await ensure_user(update, context)
    data = query.data or ""

    if data.startswith("menu:"):
        action = data.split(":", 1)[1]
        if action == "practice":
            await start_practice(update, context, user)
        elif action == "progress":
            await progress(update, context)
        elif action == "settings":
            await settings(update, context)
        elif action == "subscription":
            await subscription(update, context)
        return

    if data.startswith("onb:"):
        await handle_onboarding_callback(update, context, user, data)


async def handle_onboarding_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    callback_data: str,
) -> None:
    db: Database = context.application.bot_data["db"]
    _, step, value = callback_data.split(":", 2)
    data = dict(user.get("onboarding_data") or {})

    if step == "topics":
        selected = list(data.get("topics") or [])
        if value in selected:
            selected.remove(value)
        else:
            selected.append(value)
        data["topics"] = selected
        await db.update_onboarding_data(user["telegram_id"], data, "topics")
        await update.callback_query.edit_message_reply_markup(reply_markup=topics_keyboard(selected))
        return

    if step == "topics_done":
        if not data.get("topics"):
            await update.callback_query.message.reply_text("Выбери хотя бы одну тему.")
            return
        await db.update_onboarding_data(user["telegram_id"], data, "correction_style")
        await ask_onboarding_step(update, context, "correction_style", data)
        return

    data[step] = value
    next_step = _next_onboarding_step(step)
    if next_step is None:
        await db.complete_onboarding(user["telegram_id"], data)
        completed_user = await db.get_user(user["telegram_id"])
        if completed_user:
            settings_obj: Settings = context.application.bot_data["settings"]
            schedule_user_reminder(context.application, completed_user, settings_obj.app_timezone)
        await update.callback_query.message.reply_text(
            "Готово. Профиль сохранен. Можем провести первую бесплатную сессию.",
            reply_markup=main_menu(data.get("interface_language")),
        )
        return

    await db.update_onboarding_data(user["telegram_id"], data, next_step)
    await ask_onboarding_step(update, context, next_step, data)


async def ask_onboarding_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    step: str,
    data: dict[str, Any],
) -> None:
    db: Database = context.application.bot_data["db"]
    if update.effective_user:
        await db.set_onboarding_step(update.effective_user.id, step)

    message = update.effective_message
    if update.callback_query and update.callback_query.message:
        message = update.callback_query.message

    if step == "english_level":
        await message.reply_text(
            "1/6. Какой у тебя примерный уровень английского?",
            reply_markup=option_keyboard(step, LEVEL_OPTIONS),
        )
    elif step == "goal":
        await message.reply_text(
            "2/6. Для чего тебе английский?",
            reply_markup=option_keyboard(step, GOAL_OPTIONS),
        )
    elif step == "topics":
        await message.reply_text(
            "3/6. Какие темы интересны? Можно выбрать несколько.",
            reply_markup=topics_keyboard(data.get("topics") or []),
        )
    elif step == "correction_style":
        await message.reply_text(
            "4/6. Какой стиль исправлений предпочитаешь?",
            reply_markup=option_keyboard(step, CORRECTION_OPTIONS),
        )
    elif step == "reminder_time":
        await message.reply_text(
            "5/6. Во сколько напоминать о практике?",
            reply_markup=option_keyboard(step, REMINDER_OPTIONS),
        )
    elif step == "interface_language":
        await message.reply_text(
            "6/6. Предпочитаемый язык интерфейса:",
            reply_markup=option_keyboard(step, LANGUAGE_OPTIONS),
        )


async def start_practice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
) -> None:
    if not user["onboarding_completed"]:
        await update.effective_message.reply_text("Сначала закончим короткий онбординг.")
        await ask_onboarding_step(
            update,
            context,
            user.get("onboarding_step") or "english_level",
            user.get("onboarding_data") or {},
        )
        return

    db: Database = context.application.bot_data["db"]
    existing = await db.get_active_session(user["telegram_id"])
    if existing:
        await update.effective_message.reply_text(
            f"Continue the current topic: {existing['topic_title']}\n\n"
            "Send a voice message or type your answer.",
            reply_markup=practice_reply_keyboard(),
        )
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    topic_selector: TopicSelector = context.application.bot_data["topic_selector"]
    memories = await db.get_recent_memories(user["telegram_id"], limit=5)
    recent_topics = await db.get_recent_topics(user["telegram_id"], limit=8)
    try:
        topic = await topic_selector.select(profile=user, memories=memories, recent_topics=recent_topics)
    except Exception:
        logger.exception("Topic selection failed; using fallback topic")
        topic = fallback_topic()
    session_id = await db.create_session(user["telegram_id"], topic.model_dump())
    await db.add_message(session_id, "tutor", topic.opening_question)

    text = f"Today's topic: {topic.title}\n\n{topic.opening_question}"
    await send_text_and_voice(update, context, text, topic.opening_question, practice_reply_keyboard())


async def handle_practice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    if update.effective_message.text and update.effective_message.text.startswith("/"):
        return

    user = await ensure_user(update, context)
    if not user["onboarding_completed"]:
        await update.effective_message.reply_text("Пока отвечай кнопками в онбординге.")
        return

    db: Database = context.application.bot_data["db"]
    session = await db.get_active_session(user["telegram_id"])
    if not session:
        await update.effective_message.reply_text(
            "Start a practice session first.",
            reply_markup=main_menu(user.get("interface_language")),
        )
        return

    user_text = await extract_user_text(update, context)
    if not user_text:
        await update.effective_message.reply_text("I could not understand that. Try again.")
        return

    await db.add_message(session["id"], "user", user_text, _voice_file_id(update))
    turn_number = int(session["turn_count"]) + 1
    await db.increment_turn_count(session["id"])

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    messages = await db.get_session_messages(session["id"], limit=20)
    tutor: Tutor = context.application.bot_data["tutor"]
    settings_obj: Settings = context.application.bot_data["settings"]
    try:
        reply = await tutor.respond(
            profile=user,
            session=session,
            messages=messages,
            user_message=user_text,
            turn_number=turn_number,
            min_turns=settings_obj.min_dialogue_turns,
            max_turns=settings_obj.max_dialogue_turns,
        )
    except Exception:
        logger.exception("Tutor response failed; using fallback reply")
        should_finish = turn_number >= settings_obj.max_dialogue_turns
        follow_up = None if should_finish else "Can you give one concrete example?"
        reply = TutorReply(
            reply="I understand your idea. Let's make it a little more specific.",
            follow_up=follow_up,
            soft_correction=None,
            should_finish=should_finish,
        )
    reply_text = reply.text_for_user()
    await db.add_message(session["id"], "tutor", reply_text)
    await send_text_and_voice(update, context, reply_text, reply_text, practice_reply_keyboard())

    if reply.should_finish:
        fresh_session = await db.get_session(session["id"])
        if fresh_session:
            await finish_session(update, context, user, fresh_session)


async def extract_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    if message.text:
        return message.text.strip()

    if not message.voice:
        return ""

    settings_obj: Settings = context.application.bot_data["settings"]
    speech_to_text: SpeechToText = context.application.bot_data["speech_to_text"]
    incoming_path = settings_obj.audio_dir / f"incoming-{uuid.uuid4().hex}.ogg"

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    voice_file = await message.voice.get_file()
    await voice_file.download_to_drive(custom_path=incoming_path)
    try:
        transcript = await speech_to_text.transcribe(incoming_path)
    finally:
        incoming_path.unlink(missing_ok=True)

    if transcript:
        await message.reply_text(f"I heard: {transcript}")
    return transcript


async def finish_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    session: dict[str, Any],
) -> None:
    db: Database = context.application.bot_data["db"]
    evaluator: Evaluator = context.application.bot_data["evaluator"]
    memory_updater: MemoryUpdater = context.application.bot_data["memory_updater"]

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    messages = await db.get_session_messages(session["id"], limit=40)
    try:
        feedback = await evaluator.evaluate(profile=user, session=session, messages=messages)
    except Exception:
        logger.exception("Evaluation failed; using fallback feedback")
        feedback = fallback_feedback()
    await db.complete_session(session["id"], feedback.summary, feedback.model_dump())

    try:
        memory_update = await memory_updater.update(
            profile=user,
            session=session,
            messages=messages,
            feedback=feedback,
        )
        await db.add_memories(
            user["telegram_id"],
            [memory.model_dump() for memory in memory_update.memories],
        )
    except Exception:
        logger.exception("Failed to update memory")

    await update.effective_message.reply_text(format_feedback(feedback), reply_markup=main_menu())


async def send_text_and_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    voice_text: str,
    reply_markup: Any | None = None,
) -> None:
    message = update.effective_message
    await message.reply_text(text, reply_markup=reply_markup)
    tts: TextToSpeech = context.application.bot_data["text_to_speech"]
    try:
        audio_path = await tts.synthesize(voice_text)
        try:
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.RECORD_VOICE)
            with audio_path.open("rb") as audio_file:
                await context.bot.send_voice(chat_id=update.effective_chat.id, voice=audio_file)
        finally:
            audio_path.unlink(missing_ok=True)
    except Exception:
        logger.exception("TTS failed; text response was already sent")


async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    db: Database = context.application.bot_data["db"]
    telegram_user = update.effective_user
    chat = update.effective_chat
    if telegram_user is None or chat is None:
        raise RuntimeError("Telegram update has no effective user or chat")
    return await db.upsert_user(
        telegram_id=telegram_user.id,
        chat_id=chat.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )


def _next_onboarding_step(step: str) -> str | None:
    index = ONBOARDING_ORDER.index(step)
    if index + 1 >= len(ONBOARDING_ORDER):
        return None
    return ONBOARDING_ORDER[index + 1]


def _voice_file_id(update: Update) -> str | None:
    message = update.effective_message
    if message and message.voice:
        return message.voice.file_id
    return None


def fallback_topic() -> TopicChoice:
    return TopicChoice(
        topic_id="daily_choices",
        title="Daily choices",
        opening_question="What is one small decision today that could make your week better?",
        rationale="Useful general topic for any level.",
    )


def fallback_feedback() -> Feedback:
    return Feedback.model_validate(
        {
            "summary": "You completed a short English speaking practice session.",
            "main_strength": "You communicated your idea clearly enough to continue a dialogue.",
            "main_issue": "Try to add more concrete examples and use fuller sentences.",
            "improved_phrases": [
                {"original": "I think yes", "improved": "I tend to agree because..."},
                {"original": "It is good for me", "improved": "It works well for me because..."},
            ],
            "micro_homework": "Record a 60-second answer with one reason and one example.",
            "estimated_cefr": "B1",
            "scores": [
                {"name": "Clarity", "score": 3, "note": "Mostly understandable."},
                {"name": "Vocabulary", "score": 3, "note": "Enough for the topic."},
                {"name": "Grammar", "score": 3, "note": "Some simple patterns need tightening."},
                {"name": "Argumentation", "score": 3, "note": "Add more examples."},
            ],
        }
    )
