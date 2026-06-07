from __future__ import annotations

from mindup_bot.ai.schemas import Feedback


def progress_bar(percent: int, width: int = 10) -> str:
    safe_percent = max(0, min(100, percent))
    filled = round((safe_percent / 100) * width)
    return "▰" * filled + "▱" * (width - filled)


def format_feedback(feedback: Feedback) -> str:
    phrases = "\n".join(
        f"- {item.original} -> {item.improved}" for item in feedback.improved_phrases
    )
    scores = "\n".join(f"- {item.name}: {item.score}/5 - {item.note}" for item in feedback.scores)
    return (
        "🧾 Разбор сессии\n"
        "━━━━━━━━━━━━\n\n"
        f"📌 Summary: {feedback.summary}\n\n"
        f"✅ Main strength: {feedback.main_strength}\n\n"
        f"🎯 Main issue: {feedback.main_issue}\n\n"
        "💬 Better phrases:\n"
        f"{phrases}\n\n"
        f"🏠 Micro-homework: {feedback.micro_homework}\n\n"
        f"🏆 Estimated CEFR: {feedback.estimated_cefr}\n\n"
        "📊 Scores:\n"
        f"{scores}"
    )


def format_profile(user: dict, progress: dict) -> str:
    completed = progress["completed_count"]
    display_name = user.get("first_name") or user.get("username") or "Пользователь"
    level = user.get("english_level") or "Not set"
    goal = user.get("goal") or "not set"
    topics = ", ".join(user.get("topics") or []) or "not set"

    if completed == 0:
        return (
            f"👤 {display_name}\n\n"
            f"🏆 Уровень: {level}\n"
            "🔥 Сессий: 0\n"
            f"📈 Прогресс: {progress_bar(0)} 0%\n\n"
            f"🎯 Цель: {goal}\n"
            f"📚 Темы: {topics}\n\n"
            "🚀 Начни первую практику, чтобы dialogum собрал статистику."
        )

    feedback = progress.get("last_feedback") or {}
    cefr = feedback.get("estimated_cefr", "unknown")
    summary = progress.get("last_summary") or "No summary saved."
    percent = min(100, completed * 7)
    return (
        f"👤 {display_name}\n\n"
        f"🏆 Уровень: {cefr}\n"
        f"🔥 Сессий: {completed}\n"
        f"📈 До следующего уровня: {progress_bar(percent)} {percent}%\n\n"
        f"🎯 Цель: {goal}\n"
        f"📚 Темы: {topics}\n\n"
        f"🧾 Последняя сессия: {summary}"
    )


def format_settings(user: dict) -> str:
    topics = ", ".join(user.get("topics") or []) or "not set"
    return (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━\n\n"
        f"🏆 Уровень: {user.get('english_level') or 'not set'}\n"
        f"🎯 Цель: {user.get('goal') or 'not set'}\n"
        f"📚 Темы: {topics}\n"
        f"🧾 Исправления: {user.get('correction_style') or 'not set'}\n"
        f"🔔 Напоминание: {user.get('reminder_time') or 'not set'}\n"
        f"🌐 Интерфейс: {user.get('interface_language') or 'not set'}"
    )


def format_help() -> str:
    return (
        "📖 Что умеет dialogum?\n"
        "━━━━━━━━━━━━\n\n"
        "🎙 Дает короткое speaking-задание на английском.\n"
        "💬 Ведет диалог и задает уточняющие вопросы.\n"
        "🧾 После сессии показывает ошибки и улучшенные фразы.\n"
        "🧠 Запоминает цели, темы и типичные слабые места.\n\n"
        "Формат: 10 минут в день, voice или текст."
    )
