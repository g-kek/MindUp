from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mindup_bot.ai.gemini_retry import TransientGeminiError
from mindup_bot.ai.roles import (
    Evaluator,
    MemoryUpdater,
    ProgressAnalyzer,
    TopicSelector,
    Translator,
    Tutor,
    VocabularyExtractor,
)
from mindup_bot.ai.schemas import Feedback, ProgressInsight, TopicChoice, TutorReply
from mindup_bot.bot.formatters import (
    format_feedback,
    format_help,
    format_profile,
    format_progress_insight,
    format_settings,
    format_vocabulary,
)
from mindup_bot.bot.keyboards import (
    CORRECTION_OPTIONS,
    CUSTOM_TOPIC_LABEL,
    CUSTOM_TOPIC_LABEL_EN,
    FINISH_LABEL,
    FINISH_LABEL_EN,
    GOAL_OPTIONS,
    HELP_LABEL,
    HELP_LABEL_EN,
    LANGUAGE_OPTIONS,
    LEVEL_OPTIONS,
    MENU_LABEL,
    MENU_LABEL_EN,
    PROFILE_LABEL,
    PROFILE_LABEL_EN,
    REMINDER_OPTIONS,
    SETTINGS_LABEL,
    SETTINGS_LABEL_EN,
    START_PRACTICE_LABEL,
    START_PRACTICE_LABEL_EN,
    VOCABULARY_LABEL,
    VOCABULARY_LABEL_EN,
    main_menu,
    option_keyboard,
    practice_message_keyboard,
    practice_reply_keyboard_for,
    settings_keyboard,
    settings_option_keyboard,
    settings_options_for,
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
    application.add_handler(CommandHandler("topic", custom_topic))
    application.add_handler(CommandHandler("vocabulary", vocabulary))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.VOICE | filters.TEXT, handle_practice_message))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if user["onboarding_completed"]:
        language = user.get("interface_language")
        text = "👋 dialogum\n\nChoose an action:" if language == "en" else "👋 dialogum\n\nВыбери действие:"
        await update.effective_message.reply_text(
            text,
            reply_markup=main_menu(language),
        )
        return

    await update.effective_message.reply_text(
        "👋 Привет! Я dialogum — твой AI-тренер английского.\n\n"
        "Я проверяю твои ответы, слежу за прогрессом и подстраиваюсь под твой уровень."
    )
    await update.effective_message.reply_text(
        "Чтобы начать — пройди короткую настройку. Это займет 3 минуты 🎯",
        reply_markup=main_menu(user.get("interface_language")),
    )
    await ask_onboarding_step(update, context, "english_level", user.get("onboarding_data", {}))


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    language = user.get("interface_language")
    text = "🏠 dialogum menu\n\nChoose an action:" if language == "en" else (
        "🏠 Меню dialogum\n\nВыбери действие:"
    )
    await update.effective_message.reply_text(
        text,
        reply_markup=main_menu(language),
    )


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    db: Database = context.application.bot_data["db"]
    data = await db.get_progress(user["telegram_id"])
    language = user.get("interface_language")
    since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    recent_sessions = await db.get_completed_sessions(user["telegram_id"], limit=8)
    last_day_sessions = await db.get_completed_sessions_since(user["telegram_id"], since, limit=8)
    if recent_sessions:
        progress_analyzer: ProgressAnalyzer = context.application.bot_data["progress_analyzer"]
        try:
            insight = await progress_analyzer.analyze(
                profile=user,
                recent_sessions=recent_sessions,
                last_day_sessions=last_day_sessions,
                language="en" if language == "en" else "ru",
            )
            await db.add_progress_report(user["telegram_id"], "recent", insight.model_dump())
        except Exception:
            logger.exception("Progress analysis failed; using fallback report")
            insight = fallback_progress_insight(language, data)
    else:
        insight = fallback_progress_insight(language, data)

    await update.effective_message.reply_text(
        f"{format_profile(user, data)}\n\n{format_progress_insight(insight, language)}",
        reply_markup=main_menu(user.get("interface_language")),
    )


async def custom_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    language = user.get("interface_language")
    if not user["onboarding_completed"]:
        message = "Let's finish setup first." if language == "en" else "Сначала закончим настройку."
        await update.effective_message.reply_text(message)
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
        message = (
            "Finish the current session before choosing a custom topic."
            if language == "en"
            else "Сначала заверши текущую сессию, потом выберем свою тему."
        )
        await update.effective_message.reply_text(
            message,
            reply_markup=practice_reply_keyboard_for(language),
        )
        return

    await db.set_custom_topic_pending(user["telegram_id"], True)
    message = (
        "Send the topic you want to discuss. One phrase is enough."
        if language == "en"
        else "Напиши тему, которую хочешь обсудить. Достаточно одной фразы."
    )
    await update.effective_message.reply_text(message, reply_markup=main_menu(language))


async def vocabulary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    db: Database = context.application.bot_data["db"]
    items = await db.get_vocabulary_items(user["telegram_id"], limit=30)
    await update.effective_message.reply_text(
        format_vocabulary(items, user.get("interface_language")),
        reply_markup=main_menu(user.get("interface_language")),
    )


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    await update.effective_message.reply_text(
        format_settings(user),
        reply_markup=settings_keyboard(user.get("interface_language")),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    await update.effective_message.reply_text(
        format_help(user.get("interface_language")),
        reply_markup=main_menu(user.get("interface_language")),
    )


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    db: Database = context.application.bot_data["db"]
    session = await db.get_active_session(user["telegram_id"])
    if not session:
        message = "No active session right now." if user.get("interface_language") == "en" else (
            "Сейчас нет активной сессии."
        )
        await update.effective_message.reply_text(
            message,
            reply_markup=main_menu(user.get("interface_language")),
        )
        return
    await finish_session(update, context, user, session)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    user = await ensure_user(update, context)
    data = query.data or ""

    if data.startswith("menu:"):
        await query.answer()
        action = data.split(":", 1)[1]
        if action == "practice":
            await start_practice(update, context, user)
        elif action == "progress":
            await progress(update, context)
        elif action == "settings":
            await settings(update, context)
        elif action == "help":
            await help_command(update, context)
        return

    if data.startswith("practice:"):
        await handle_practice_callback(update, context, user, data)
        return

    if data.startswith("onb:"):
        await handle_onboarding_callback(update, context, user, data)
        return

    if data.startswith("settings:"):
        await handle_settings_callback(update, context, user, data)


async def handle_practice_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    callback_data: str,
) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    parts = callback_data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    language = user.get("interface_language")

    if action == "finish":
        await query.answer()
        await finish(update, context)
        return

    if action == "menu":
        await query.answer()
        await menu(update, context)
        return

    if action == "translate" and len(parts) >= 3:
        db: Database = context.application.bot_data["db"]
        try:
            message_id = int(parts[2])
        except ValueError:
            await query.answer("Invalid message" if language == "en" else "Некорректное сообщение")
            return

        message = await db.get_message_for_user(message_id, user["telegram_id"])
        if not message or message.get("role") != "tutor":
            await query.answer(
                "Nothing to translate" if language == "en" else "Нечего переводить",
                show_alert=True,
            )
            return

        await query.answer()
        await context.bot.send_chat_action(query.message.chat_id, ChatAction.TYPING)
        translator: Translator = context.application.bot_data["translator"]
        try:
            translated = await translator.translate(
                text=message["content"],
                language="en" if language == "en" else "ru",
            )
            text = translated.translation
        except Exception:
            logger.exception("Translation failed")
            text = (
                "Translation is temporarily unavailable."
                if language == "en"
                else "Перевод временно недоступен."
            )

        title = "Translation" if language == "en" else "Перевод"
        await query.message.reply_text(f"🔎 {title}\n\n{text}")


async def handle_onboarding_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    callback_data: str,
) -> None:
    db: Database = context.application.bot_data["db"]
    query = update.callback_query
    if query is None:
        return
    _, step, value = callback_data.split(":", 2)
    data = dict(user.get("onboarding_data") or {})

    if step == "topics_done" and not data.get("topics"):
        await query.answer("Выбери хотя бы одну тему.", show_alert=True)
        return

    await query.answer()

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
            progress_data = await db.get_progress(completed_user["telegram_id"])
            header = (
                "✅ Setup complete. Here is your profile:\n\n"
                if completed_user.get("interface_language") == "en"
                else "✅ Настройка завершена. Вот твой профиль:\n\n"
            )
            await update.callback_query.message.reply_text(
                header + format_profile(completed_user, progress_data),
                reply_markup=main_menu(completed_user.get("interface_language")),
            )
            return

        done_text = "Готово. Профиль сохранен. Можем провести первую бесплатную сессию."
        await update.callback_query.message.reply_text(
            done_text,
            reply_markup=main_menu(data.get("interface_language")),
        )
        return

    await db.update_onboarding_data(user["telegram_id"], data, next_step)
    await ask_onboarding_step(update, context, next_step, data)


async def handle_settings_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    callback_data: str,
) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return
    await query.answer()

    db: Database = context.application.bot_data["db"]
    language = user.get("interface_language")
    parts = callback_data.split(":")

    if len(parts) >= 2 and parts[1] == "back":
        fresh_user = await db.get_user(user["telegram_id"])
        if fresh_user is None:
            return
        await edit_callback_message(
            query,
            format_settings(fresh_user),
            reply_markup=settings_keyboard(fresh_user.get("interface_language")),
        )
        return

    if len(parts) >= 2 and parts[1] == "close":
        text = (
            "🏠 dialogum menu\n\nUse the keyboard below to choose an action."
            if language == "en"
            else "🏠 Меню dialogum\n\nВыбери действие на клавиатуре ниже."
        )
        await edit_callback_message(query, text, reply_markup=None)
        return

    if len(parts) >= 3 and parts[1] == "edit":
        field = parts[2]
        if field == "topics":
            text = "📚 Choose topics:" if language == "en" else "📚 Выбери темы:"
            await edit_callback_message(
                query,
                text,
                reply_markup=topics_keyboard(
                    user.get("topics") or [],
                    mode="settings",
                    language=language,
                ),
            )
            return

        prompts = {
            "english_level": ("🏆 Choose your level:", "🏆 Выбери уровень:"),
            "goal": ("🎯 Choose your goal:", "🎯 Выбери цель:"),
            "correction_style": ("🧾 Choose correction style:", "🧾 Выбери стиль исправлений:"),
            "reminder_time": ("🔔 Choose reminder time:", "🔔 Выбери время напоминания:"),
            "tts_voice": ("🔊 Choose bot voice:", "🔊 Выбери голос бота:"),
            "interface_language": ("🌐 Choose interface language:", "🌐 Выбери язык интерфейса:"),
        }
        if field not in prompts:
            return
        prompt_en, prompt_ru = prompts[field]
        await edit_callback_message(
            query,
            prompt_en if language == "en" else prompt_ru,
            reply_markup=settings_option_keyboard(field, settings_options_for(field, language), language),
        )
        return

    if len(parts) >= 4 and parts[1] == "set":
        field = parts[2]
        value = parts[3]
        await db.update_user_settings(user["telegram_id"], {field: value})
        fresh_user = await db.get_user(user["telegram_id"])
        if fresh_user is None:
            return
        if field == "reminder_time":
            settings_obj: Settings = context.application.bot_data["settings"]
            schedule_user_reminder(context.application, fresh_user, settings_obj.app_timezone)

        await edit_callback_message(
            query,
            format_settings(fresh_user),
            reply_markup=settings_keyboard(fresh_user.get("interface_language")),
        )
        return

    if len(parts) >= 3 and parts[1] == "topic":
        topic = parts[2]
        selected = list(user.get("topics") or [])
        if topic in selected:
            selected.remove(topic)
        else:
            selected.append(topic)
        await db.update_user_settings(user["telegram_id"], {"topics": selected})
        await query.edit_message_reply_markup(
            reply_markup=topics_keyboard(selected, mode="settings", language=language)
        )
        return

    if len(parts) >= 3 and parts[1] == "topics_done":
        fresh_user = await db.get_user(user["telegram_id"])
        if fresh_user is None:
            return
        await edit_callback_message(
            query,
            format_settings(fresh_user),
            reply_markup=settings_keyboard(fresh_user.get("interface_language")),
        )


async def ask_onboarding_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    step: str,
    data: dict[str, Any],
) -> None:
    db: Database = context.application.bot_data["db"]
    if update.effective_user:
        await db.set_onboarding_step(update.effective_user.id, step)

    if step == "english_level":
        await send_or_edit_inline(
            update,
            "🏆 Вопрос 1 из 6\n"
            "Прогресс: ▰▱▱▱▱▱ 17%\n\n"
            "Какой у тебя примерный уровень английского?",
            reply_markup=option_keyboard(step, LEVEL_OPTIONS),
        )
    elif step == "goal":
        await send_or_edit_inline(
            update,
            "🎯 Вопрос 2 из 6\n"
            "Прогресс: ▰▰▱▱▱▱ 33%\n\n"
            "Для чего тебе английский?",
            reply_markup=option_keyboard(step, GOAL_OPTIONS),
        )
    elif step == "topics":
        await send_or_edit_inline(
            update,
            "📚 Вопрос 3 из 6\n"
            "Прогресс: ▰▰▰▱▱▱ 50%\n\n"
            "Какие темы интересны? Можно выбрать несколько.",
            reply_markup=topics_keyboard(data.get("topics") or []),
        )
    elif step == "correction_style":
        await send_or_edit_inline(
            update,
            "🧾 Вопрос 4 из 6\n"
            "Прогресс: ▰▰▰▰▱▱ 67%\n\n"
            "Какой стиль исправлений предпочитаешь?",
            reply_markup=option_keyboard(step, CORRECTION_OPTIONS),
        )
    elif step == "reminder_time":
        await send_or_edit_inline(
            update,
            "🔔 Вопрос 5 из 6\n"
            "Прогресс: ▰▰▰▰▰▱ 83%\n\n"
            "Во сколько напоминать о практике?",
            reply_markup=option_keyboard(step, REMINDER_OPTIONS),
        )
    elif step == "interface_language":
        await send_or_edit_inline(
            update,
            "🌐 Вопрос 6 из 6\n"
            "Прогресс: ▰▰▰▰▰▰ 100%\n\n"
            "Предпочитаемый язык интерфейса:",
            reply_markup=option_keyboard(step, LANGUAGE_OPTIONS),
        )


async def start_practice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
) -> None:
    if not user["onboarding_completed"]:
        message = "Let's finish the quick setup first." if user.get("interface_language") == "en" else (
            "Сначала закончим короткую настройку."
        )
        await update.effective_message.reply_text(message)
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
        if user.get("interface_language") == "en":
            message = (
                f"▶️ Continuing topic: {existing['topic_title']}\n\n"
                "Send a voice message or type your answer in English."
            )
        else:
            message = (
                f"▶️ Продолжаем тему: {existing['topic_title']}\n\n"
                "Отправь voice или напиши ответ на английском."
            )
        await update.effective_message.reply_text(
            message,
            reply_markup=practice_reply_keyboard_for(user.get("interface_language")),
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
    message_id = await db.add_message(session_id, "tutor", topic.opening_question)

    if user.get("interface_language") == "en":
        text = (
            "🎙 Speaking · Task\n"
            "━━━━━━━━━━━━\n\n"
            f"{topic.opening_question}\n\n"
            "⏱ Recording: up to 60 seconds\n"
            "👇 Send a voice message or type your answer"
        )
    else:
        text = (
            "🎙 Speaking · Задание\n"
            "━━━━━━━━━━━━\n\n"
            f"{topic.opening_question}\n\n"
            "⏱ Запись: до 60 секунд\n"
            "👇 Отправь голосовое сообщение или напиши ответ"
        )
    await send_text_and_voice(
        update,
        context,
        text,
        topic.opening_question,
        practice_message_keyboard(message_id, user.get("interface_language")),
        voice=user.get("tts_voice"),
    )


async def start_custom_topic_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    requested_topic: str,
) -> None:
    db: Database = context.application.bot_data["db"]
    existing = await db.get_active_session(user["telegram_id"])
    if existing:
        message = (
            "Finish the current session before starting a new topic."
            if user.get("interface_language") == "en"
            else "Сначала заверши текущую сессию, потом начнем новую тему."
        )
        await update.effective_message.reply_text(
            message,
            reply_markup=practice_reply_keyboard_for(user.get("interface_language")),
        )
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    topic_selector: TopicSelector = context.application.bot_data["topic_selector"]
    try:
        topic = await topic_selector.from_custom_topic(
            profile=user,
            requested_topic=requested_topic,
        )
    except Exception:
        logger.exception("Custom topic creation failed; using fallback topic")
        topic = fallback_custom_topic(requested_topic)

    session_id = await db.create_session(user["telegram_id"], topic.model_dump())
    message_id = await db.add_message(session_id, "tutor", topic.opening_question)
    if user.get("interface_language") == "en":
        text = (
            f"🎙 Speaking · {topic.title}\n"
            "━━━━━━━━━━━━\n\n"
            f"{topic.opening_question}\n\n"
            "⏱ Recording: up to 60 seconds\n"
            "👇 Send a voice message or type your answer"
        )
    else:
        text = (
            f"🎙 Speaking · {topic.title}\n"
            "━━━━━━━━━━━━\n\n"
            f"{topic.opening_question}\n\n"
            "⏱ Запись: до 60 секунд\n"
            "👇 Отправь голосовое сообщение или напиши ответ"
        )

    await send_text_and_voice(
        update,
        context,
        text,
        topic.opening_question,
        practice_message_keyboard(message_id, user.get("interface_language")),
        voice=user.get("tts_voice"),
    )


async def handle_practice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    if update.effective_message.text and update.effective_message.text.startswith("/"):
        return

    user = await ensure_user(update, context)
    if update.effective_message.text:
        text = update.effective_message.text.strip()
        if await handle_menu_text(update, context, user, text):
            return

    if not user["onboarding_completed"]:
        message = "For now, answer with onboarding buttons." if user.get("interface_language") == "en" else (
            "Пока отвечай кнопками в онбординге."
        )
        await update.effective_message.reply_text(message)
        return

    db: Database = context.application.bot_data["db"]
    if update.effective_message.text and user.get("custom_topic_pending"):
        requested_topic = update.effective_message.text.strip()
        await db.set_custom_topic_pending(user["telegram_id"], False)
        await start_custom_topic_session(update, context, user, requested_topic)
        return

    session = await db.get_active_session(user["telegram_id"])
    if not session:
        message = "Start a practice session first." if user.get("interface_language") == "en" else (
            "Сначала начни практику."
        )
        await update.effective_message.reply_text(
            message,
            reply_markup=main_menu(user.get("interface_language")),
        )
        return

    user_text = await extract_user_text(update, context)
    if not user_text:
        message = "I could not understand that. Try again." if user.get("interface_language") == "en" else (
            "Не смог разобрать сообщение. Попробуй еще раз."
        )
        await update.effective_message.reply_text(message)
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
    message_id = await db.add_message(session["id"], "tutor", reply_text)
    await send_text_and_voice(
        update,
        context,
        reply_text,
        reply_text,
        practice_message_keyboard(message_id, user.get("interface_language")),
        voice=user.get("tts_voice"),
    )

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
    except TransientGeminiError:
        logger.exception("Voice transcription failed because Gemini is temporarily unavailable")
        user = await ensure_user(update, context)
        if user.get("interface_language") == "en":
            await message.reply_text(
                "Speech recognition is temporarily unavailable. Please type your answer."
            )
        else:
            await message.reply_text(
                "Распознавание голоса временно недоступно. Напиши ответ текстом."
            )
        return ""
    finally:
        incoming_path.unlink(missing_ok=True)

    if transcript:
        duration = message.voice.duration if message.voice else 0
        telegram_user = update.effective_user
        db: Database = context.application.bot_data["db"]
        user = await db.get_user(telegram_user.id) if telegram_user else None
        if user and user.get("interface_language") == "en":
            await message.reply_text(
                f"🎤 Voice message · {duration} sec\n\n"
                f"Transcript: {transcript}\n\n"
                "🔄 Analyzing your speech...\nAI is listening and preparing a reply 👂"
            )
        else:
            await message.reply_text(
                f"🎤 Голосовое сообщение · {duration} сек\n\n"
                f"Расшифровка: {transcript}\n\n"
                "🔄 Анализирую твою речь...\nAI слушает и готовит ответ 👂"
            )
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
    language = "en" if user.get("interface_language") == "en" else "ru"
    try:
        feedback = await evaluator.evaluate(
            profile=user,
            session=session,
            messages=messages,
            language=language,
        )
    except Exception:
        logger.exception("Evaluation failed; using fallback feedback")
        feedback = fallback_feedback(language)
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

    vocabulary_extractor: VocabularyExtractor = context.application.bot_data["vocabulary_extractor"]
    try:
        vocabulary_update = await vocabulary_extractor.extract(
            profile=user,
            session=session,
            messages=messages,
            feedback=feedback,
            language=language,
        )
        await db.upsert_vocabulary_items(
            user["telegram_id"],
            session["id"],
            [phrase.model_dump() for phrase in vocabulary_update.phrases],
        )
    except Exception:
        logger.exception("Failed to update vocabulary; using feedback phrases")
        await db.upsert_vocabulary_items(
            user["telegram_id"],
            session["id"],
            fallback_vocabulary_from_feedback(feedback, language),
        )

    await update.effective_message.reply_text(
        format_feedback(feedback, user.get("interface_language")),
        reply_markup=main_menu(user.get("interface_language")),
    )


async def send_text_and_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    voice_text: str,
    reply_markup: Any | None = None,
    voice: str | None = None,
) -> None:
    message = update.effective_message
    await message.reply_text(text, reply_markup=reply_markup)
    tts: TextToSpeech = context.application.bot_data["text_to_speech"]
    try:
        audio_path = await tts.synthesize(voice_text, voice=voice)
        try:
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.RECORD_VOICE)
            with audio_path.open("rb") as audio_file:
                await context.bot.send_voice(chat_id=update.effective_chat.id, voice=audio_file)
        finally:
            audio_path.unlink(missing_ok=True)
    except Exception:
        logger.exception("TTS failed; text response was already sent")


async def send_or_edit_inline(update: Update, text: str, reply_markup: Any) -> None:
    if update.callback_query is not None:
        await edit_callback_message(update.callback_query, text, reply_markup=reply_markup)
        return
    await update.effective_message.reply_text(text, reply_markup=reply_markup)


async def edit_callback_message(query: Any, text: str, reply_markup: Any) -> None:
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        raise


async def handle_menu_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict[str, Any],
    text: str,
) -> bool:
    normalized = text.strip()
    if normalized in {START_PRACTICE_LABEL, START_PRACTICE_LABEL_EN}:
        await start_practice(update, context, user)
        return True
    if normalized in {PROFILE_LABEL, PROFILE_LABEL_EN}:
        await progress(update, context)
        return True
    if normalized in {CUSTOM_TOPIC_LABEL, CUSTOM_TOPIC_LABEL_EN}:
        await custom_topic(update, context)
        return True
    if normalized in {VOCABULARY_LABEL, VOCABULARY_LABEL_EN}:
        await vocabulary(update, context)
        return True
    if normalized in {SETTINGS_LABEL, SETTINGS_LABEL_EN}:
        await settings(update, context)
        return True
    if normalized in {HELP_LABEL, HELP_LABEL_EN}:
        await help_command(update, context)
        return True
    if normalized in {MENU_LABEL, MENU_LABEL_EN}:
        await menu(update, context)
        return True
    if normalized in {FINISH_LABEL, FINISH_LABEL_EN}:
        await finish(update, context)
        return True
    return False


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


def fallback_custom_topic(requested_topic: str) -> TopicChoice:
    clean_topic = requested_topic.strip()[:80] or "Custom topic"
    return TopicChoice(
        topic_id=f"custom_{uuid.uuid4().hex[:8]}",
        title=clean_topic,
        opening_question=f"What is your opinion about {clean_topic}? Give one clear example.",
        rationale="The user requested this topic.",
    )


def fallback_progress_insight(language: str | None, progress_data: dict[str, Any]) -> ProgressInsight:
    completed_count = int(progress_data.get("completed_count") or 0)
    if language == "en":
        if completed_count == 0:
            return ProgressInsight(
                overall_summary="No completed sessions yet.",
                recent_change="There is not enough data to compare conversations.",
                last_day_summary="No completed practice in the last 24 hours.",
                next_focus="Finish one short session and answer with one reason plus one example.",
                achievements=[],
            )
        return ProgressInsight(
            overall_summary=f"You have completed {completed_count} practice sessions.",
            recent_change="Use the latest feedback to track recurring strengths and weak spots.",
            last_day_summary=progress_data.get("last_summary") or "No detailed last-day summary saved.",
            next_focus="Add one concrete example to every answer.",
            achievements=["You are building a regular speaking habit."],
        )

    if completed_count == 0:
        return ProgressInsight(
            overall_summary="Пока нет завершенных сессий.",
            recent_change="Недостаточно данных, чтобы сравнить разговоры.",
            last_day_summary="За последние 24 часа завершенной практики нет.",
            next_focus="Заверши одну короткую сессию и отвечай по схеме: причина плюс пример.",
            achievements=[],
        )
    return ProgressInsight(
        overall_summary=f"Ты завершил {completed_count} практических сессий.",
        recent_change="Используй последний разбор, чтобы отслеживать повторяющиеся сильные и слабые места.",
        last_day_summary=progress_data.get("last_summary") or "Детальный итог за день пока не сохранен.",
        next_focus="Добавляй один конкретный пример к каждому ответу.",
        achievements=["Ты формируешь регулярную speaking-практику."],
    )


def fallback_feedback(language: str = "ru") -> Feedback:
    if language == "en":
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

    return Feedback.model_validate(
        {
            "summary": "Ты завершил короткую speaking-сессию на английском.",
            "main_strength": "Ты достаточно ясно передал мысль, чтобы поддержать диалог.",
            "main_issue": "Старайся добавлять больше конкретных примеров и использовать более полные фразы.",
            "improved_phrases": [
                {"original": "I think yes", "improved": "I tend to agree because..."},
                {"original": "It is good for me", "improved": "It works well for me because..."},
            ],
            "micro_homework": "Запиши ответ на 60 секунд: одна причина и один пример.",
            "estimated_cefr": "B1",
            "scores": [
                {"name": "Ясность", "score": 3, "note": "В целом понятно."},
                {"name": "Словарь", "score": 3, "note": "Достаточно для темы."},
                {"name": "Грамматика", "score": 3, "note": "Некоторые простые конструкции стоит подтянуть."},
                {"name": "Аргументация", "score": 3, "note": "Добавляй больше примеров."},
            ],
        }
    )


def fallback_vocabulary_from_feedback(feedback: Feedback, language: str) -> list[dict[str, str]]:
    note = "Фраза из разбора сессии." if language == "ru" else "Phrase from the session feedback."
    return [
        {
            "phrase": phrase.improved,
            "translation": "",
            "note": note,
        }
        for phrase in feedback.improved_phrases
        if phrase.improved
    ]
