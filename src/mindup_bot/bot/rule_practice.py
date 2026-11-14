"""Interactive practice of a learner-selected rule, contrast or topic."""

from __future__ import annotations

import logging
from html import escape
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode

from mindup_bot.ai.roles import RulePracticeCoach
from mindup_bot.ai.schemas import RuleAnswerEvaluation, RuleLesson, RuleTask
from mindup_bot.bot.keyboards import main_menu, practice_reply_keyboard_for
from mindup_bot.db import Database
from mindup_bot.learning import RULES, rule_label

logger = logging.getLogger(__name__)


def lesson_intro(lesson: RuleLesson, language: str | None) -> str:
    examples = "\n\n".join(
        f"• <b>{escape(example.sentence)}</b>\n{escape(example.explanation)}"
        for example in lesson.examples
    )
    sources = "\n".join(
        f'<a href="{escape(RULES[rule][2], quote=True)}">{escape(rule_label(rule, language))}</a>'
        for rule in dict.fromkeys(lesson.focus_rules)
    )
    label = "References" if language == "en" else "Справочники"
    return f"<b>🧩 {escape(lesson.title)}</b>\n\n{escape(lesson.overview)}\n\n{examples}\n\n{label}:\n{sources}"


def task_text(task: RuleTask, index: int, total: int, language: str | None) -> str:
    label = "Task" if language == "en" else "Задание"
    text = f"<b>{label} {index + 1}/{total}</b>\n\n{escape(task.prompt)}"
    if task.choices:
        text += "\n\n" + "\n".join(
            f"{number}. {escape(option)}" for number, option in enumerate(task.choices, 1)
        )
        text += "\n\n" + ("Choose 1 or 2." if language == "en" else "Выбери 1 или 2.")
    else:
        text += "\n\n" + (
            "Send your answer as text or voice."
            if language == "en"
            else "Ответь текстом или голосом."
        )
    return text


def task_keyboard(practice_id: int, index: int, task: RuleTask, language: str | None):
    rows = []
    if task.choices:
        rows.append(
            [
                InlineKeyboardButton(
                    str(number + 1), callback_data=f"train:answer:{practice_id}:{index}:{number}"
                )
                for number in range(2)
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                "Finish training" if language == "en" else "Завершить тренировку",
                callback_data=f"train:stop:{practice_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


async def show_task(update, practice: dict[str, Any], language: str | None) -> None:
    lesson = RuleLesson.model_validate(practice["lesson"])
    index = practice["current_task"]
    await update.effective_message.reply_text(
        task_text(lesson.tasks[index], index, len(lesson.tasks), language),
        reply_markup=task_keyboard(practice["id"], index, lesson.tasks[index], language),
        parse_mode=ParseMode.HTML,
    )


async def start(update, context, user: dict[str, Any], requested_topic: str | None = None) -> None:
    db: Database = context.application.bot_data["db"]
    language = user.get("interface_language")
    if await db.get_active_session(user["telegram_id"]):
        await update.effective_message.reply_text(
            "Finish your speaking session first with /finish."
            if language == "en"
            else "Сначала заверши speaking-сессию командой /finish.",
        )
        return
    if requested_topic is not None:
        await create(update, context, user, requested_topic)
        return
    existing = await db.get_active_rule_practice(user["telegram_id"])
    if existing:
        await db.set_pending_action(user["telegram_id"], "rule_answer")
        await update.effective_message.reply_text(
            "Continuing your training. Start a new one with /train <topic or rule>."
            if language == "en"
            else "Продолжаем тренировку. Для новой напиши /train <тема или правило>.",
            reply_markup=practice_reply_keyboard_for(language),
        )
        await show_task(update, existing, language)
        return
    await db.set_pending_action(user["telegram_id"], "rule_topic")
    await update.effective_message.reply_text(
        "What would you like to practise? For example: Past Simple vs Present Perfect, "
        "in/on/at, conditionals, or travel. You can describe what confuses you."
        if language == "en"
        else "Напиши тему, правило или что тебя путает. Например: Past Simple vs Present Perfect, "
        "in/on/at, условные предложения или путешествия.",
        reply_markup=main_menu(language),
    )


async def create(update, context, user: dict[str, Any], requested_topic: str) -> None:
    db: Database = context.application.bot_data["db"]
    language = user.get("interface_language")
    requested_topic = requested_topic.strip()
    if not 1 <= len(requested_topic) <= 400:
        await db.set_pending_action(user["telegram_id"], "rule_topic")
        await update.effective_message.reply_text(
            "Describe the topic in 1–400 characters."
            if language == "en"
            else "Опиши тему текстом от 1 до 400 символов.",
        )
        return
    if await db.get_active_session(user["telegram_id"]):
        await update.effective_message.reply_text(
            "Finish the speaking session with /finish first."
            if language == "en"
            else "Сначала заверши speaking-сессию командой /finish.",
        )
        return
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    coach: RulePracticeCoach = context.application.bot_data["rule_practice_coach"]
    try:
        lesson = await coach.build(
            profile=user,
            requested_topic=requested_topic,
            language="en" if language == "en" else "ru",
        )
    except Exception:
        logger.exception("Failed to build requested rule practice")
        await db.set_pending_action(user["telegram_id"], "rule_topic")
        await update.effective_message.reply_text(
            "I couldn't prepare this training. Send the topic again to retry."
            if language == "en"
            else "Не удалось подготовить тренировку. Отправь тему ещё раз, чтобы повторить попытку.",
        )
        return
    practice_id = await db.create_rule_practice(user["telegram_id"], requested_topic, lesson)
    await update.effective_message.reply_text(
        lesson_intro(lesson, language),
        parse_mode=ParseMode.HTML,
        reply_markup=practice_reply_keyboard_for(language),
    )
    await show_task(update, await db.get_rule_practice(practice_id, user["telegram_id"]), language)


def choice_number(answer: str, task: RuleTask) -> int | None:
    normalized = answer.strip().casefold()
    if normalized in {"1", "a", "а", "one", "первый"}:
        return 0
    if normalized in {"2", "b", "б", "two", "второй"}:
        return 1
    return next(
        (
            index
            for index, option in enumerate(task.choices)
            if normalized == option.strip().casefold()
        ),
        None,
    )


async def answer(
    update,
    context,
    user: dict[str, Any],
    text: str,
    expected_id: int | None = None,
    expected_index: int | None = None,
) -> None:
    db: Database = context.application.bot_data["db"]
    language = user.get("interface_language")
    practice = await db.get_active_rule_practice(user["telegram_id"])
    if practice is None:
        await db.set_pending_action(user["telegram_id"], None)
        await update.effective_message.reply_text(
            "Start training with /train." if language == "en" else "Начни тренировку через /train.",
            reply_markup=main_menu(language),
        )
        return
    if await db.get_active_session(user["telegram_id"]):
        return
    index = practice["current_task"]
    if (expected_id is not None and expected_id != practice["id"]) or (
        expected_index is not None and expected_index != index
    ):
        return
    if not text.strip() or len(text) > 2500 or "[unclear]" in text.lower():
        await update.effective_message.reply_text(
            "Please repeat a clear answer of up to 2500 characters."
            if language == "en"
            else "Повтори, пожалуйста, разборчивый ответ до 2500 символов.",
        )
        return
    lesson = RuleLesson.model_validate(practice["lesson"])
    task = lesson.tasks[index]
    if task.kind == "choose":
        chosen = choice_number(text, task)
        if chosen is None:
            await update.effective_message.reply_text(
                "Choose 1 or 2, or send the exact option."
                if language == "en"
                else "Выбери 1 или 2 либо отправь вариант целиком.",
            )
            return
        result = RuleAnswerEvaluation(
            outcome="correct" if chosen == task.correct_choice else "incorrect",
            feedback=task.explanation,
            suggested_answer=task.answer,
            next_hint=(
                "Notice the context and what changes with the other form."
                if language == "en"
                else "Обрати внимание на контекст и на то, что меняется с другой формой."
            ),
        )
        text = task.choices[chosen]
    else:
        coach: RulePracticeCoach = context.application.bot_data["rule_practice_coach"]
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        try:
            result = await coach.check(
                profile=user,
                requested_topic=practice["requested_topic"],
                task=task,
                answer=text,
                previous_attempts=await db.get_rule_attempts(practice["id"], user["telegram_id"]),
                language="en" if language == "en" else "ru",
            )
        except Exception:
            logger.exception("Rule answer evaluation failed")
            await update.effective_message.reply_text(
                "Checking is temporarily unavailable. Send your answer again; your task is saved."
                if language == "en"
                else "Проверка временно недоступна. Отправь ответ ещё раз; задание сохранено.",
            )
            return
    saved = await db.record_rule_attempt(practice["id"], user["telegram_id"], index, text, result)
    if not saved:
        return
    labels = (
        {"correct": "✅ Correct", "partial": "🟡 Partly correct", "incorrect": "🔎 Needs work"}
        if language == "en"
        else {
            "correct": "✅ Верно",
            "partial": "🟡 Частично верно",
            "incorrect": "🔎 Нужно поправить",
        }
    )
    sample_label = "Example answer" if language == "en" else "Пример ответа"
    await update.effective_message.reply_text(
        f"<b>{labels[result.outcome]}</b>\n\n{escape(result.feedback)}\n\n"
        f"{sample_label}: <b>{escape(result.suggested_answer)}</b>\n\n{escape(result.next_hint)}",
        parse_mode=ParseMode.HTML,
    )
    fresh = await db.get_rule_practice(practice["id"], user["telegram_id"])
    if fresh["status"] == "completed":
        await summary(update, db, fresh, language)
    else:
        await db.set_pending_action(user["telegram_id"], "rule_answer")
        await show_task(update, fresh, language)


async def summary(update, db: Database, practice: dict[str, Any], language: str | None) -> None:
    attempts = await db.get_rule_attempts(practice["id"], practice["user_id"])
    counts = {
        outcome: sum(a["result"].get("outcome") == outcome for a in attempts)
        for outcome in ("correct", "partial", "incorrect")
    }
    title = "Training saved" if language == "en" else "Тренировка сохранена"
    text = (
        f"Correct: {counts['correct']}; partial: {counts['partial']}; "
        f"to revisit: {counts['incorrect']}."
        if language == "en"
        else f"Верно: {counts['correct']}; частично: {counts['partial']}; "
        f"повторить: {counts['incorrect']}."
    )
    missed = next((a for a in reversed(attempts) if a["result"].get("outcome") != "correct"), None)
    if missed:
        text += "\n\n" + missed["result"].get("next_hint", "")
    await update.effective_message.reply_text(
        f"<b>🧩 {title}</b>\n{escape(practice['requested_topic'])}\n\n{escape(text)}\n\n"
        + (
            "/train — resume or choose a new topic."
            if language == "en"
            else "/train — вернуться к тренировке или выбрать новую тему."
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(language),
    )


async def stop(update, context, user: dict[str, Any], practice_id: int | None = None) -> bool:
    db: Database = context.application.bot_data["db"]
    practice = await db.get_active_rule_practice(user["telegram_id"])
    if (
        practice is None
        and practice_id is None
        and user.get("pending_action") in {"rule_topic", "rule_answer"}
    ):
        await db.set_pending_action(user["telegram_id"], None)
        await update.effective_message.reply_text(
            "Training closed." if user.get("interface_language") == "en" else "Тренировка закрыта.",
            reply_markup=main_menu(user.get("interface_language")),
        )
        return True
    if practice is None or (practice_id is not None and practice_id != practice["id"]):
        return False
    if await db.stop_rule_practice(practice["id"], user["telegram_id"]):
        await summary(update, db, practice, user.get("interface_language"))
    return True


async def callback(update, context, user: dict[str, Any], data: str) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return
    parts = data.split(":")
    try:
        if len(parts) not in {3, 5}:
            raise ValueError("Invalid training action")
        practice_id = int(parts[2])
        index, selected = (int(parts[3]), int(parts[4])) if len(parts) == 5 else (None, None)
    except ValueError:
        await query.answer()
        return
    db: Database = context.application.bot_data["db"]
    practice = await db.get_rule_practice(practice_id, user["telegram_id"])
    if practice is None or practice["status"] != "active":
        await query.answer()
        return
    if await db.get_active_session(user["telegram_id"]):
        await query.answer("/finish → /train")
        return
    await query.answer()
    if parts[1] == "stop" and len(parts) == 3:
        await stop(update, context, user, practice_id)
    elif parts[1] == "answer" and len(parts) == 5 and selected in {0, 1}:
        lesson = RuleLesson.model_validate(practice["lesson"])
        if index != practice["current_task"] or lesson.tasks[index].kind != "choose":
            return
        if user.get("pending_action") not in {None, "rule_answer"}:
            return
        await answer(update, context, user, str(selected + 1), practice_id, index)
