from __future__ import annotations

from mindup_bot.ai.schemas import Feedback, ProgressInsight, SkillDrill, TopicVocabulary

GOAL_LABELS = {
    "ru": {
        "work": "Работа",
        "travel": "Путешествия",
        "study": "Учеба",
        "interviews": "Собеседования",
        "speaking_confidence": "Уверенность в речи",
        "thinking_self_expression": "Мышление и самовыражение",
    },
    "en": {
        "work": "Work",
        "travel": "Travel",
        "study": "Study",
        "interviews": "Interviews",
        "speaking_confidence": "Speaking confidence",
        "thinking_self_expression": "Thinking and self-expression",
    },
}

TOPIC_LABELS = {
    "ru": {
        "work_career": "Работа и карьера",
        "psychology": "Психология",
        "technology": "Технологии",
        "culture_media": "Культура и медиа",
        "everyday_life": "Повседневная жизнь",
        "business": "Бизнес",
        "society": "Общество",
        "random_smart_topics": "Умные случайные темы",
    },
    "en": {
        "work_career": "Work and career",
        "psychology": "Psychology",
        "technology": "Technology",
        "culture_media": "Culture and media",
        "everyday_life": "Everyday life",
        "business": "Business",
        "society": "Society",
        "random_smart_topics": "Random smart topics",
    },
}

CORRECTION_LABELS = {
    "ru": {
        "soft": "Мягкие исправления",
        "direct": "Прямые исправления",
        "after_session": "Только после сессии",
    },
    "en": {
        "soft": "Soft corrections",
        "direct": "Direct corrections",
        "after_session": "Only after the session",
    },
}

REMINDER_LABELS = {
    "ru": {
        "morning": "Утром",
        "afternoon": "Днем",
        "evening": "Вечером",
        "none": "Без напоминаний",
    },
    "en": {
        "morning": "Morning",
        "afternoon": "Afternoon",
        "evening": "Evening",
        "none": "No reminders",
    },
}

LANGUAGE_LABELS = {
    "ru": {"ru": "Русский", "en": "English"},
    "en": {"ru": "Russian", "en": "English"},
}

VOICE_LABELS = {
    "ru": {
        "en-US-JennyNeural": "Jenny · США, женский",
        "en-US-GuyNeural": "Guy · США, мужской",
        "en-GB-SoniaNeural": "Sonia · Британия, женский",
        "en-GB-RyanNeural": "Ryan · Британия, мужской",
    },
    "en": {
        "en-US-JennyNeural": "Jenny · US female",
        "en-US-GuyNeural": "Guy · US male",
        "en-GB-SoniaNeural": "Sonia · UK female",
        "en-GB-RyanNeural": "Ryan · UK male",
    },
}


def progress_bar(percent: int, width: int = 10) -> str:
    safe_percent = max(0, min(100, percent))
    filled = round((safe_percent / 100) * width)
    return "▰" * filled + "▱" * (width - filled)


def format_streak(progress: dict, language: str) -> str:
    streak = progress.get("streak") or {}
    current = int(streak.get("current") or 0)
    practiced_today = bool(streak.get("practiced_today"))
    if language == "en":
        status = "done today" if practiced_today else "not done today"
        return f"🔥 Streak: {current} days ({status})"
    status = "сегодня выполнено" if practiced_today else "сегодня еще нет"
    return f"🔥 Серия: {current} дн. ({status})"


def language_of(user_or_language: dict | str | None) -> str:
    if isinstance(user_or_language, dict):
        language = user_or_language.get("interface_language")
    else:
        language = user_or_language
    return "en" if language == "en" else "ru"


def label_value(kind: str, value: str | None, language: str) -> str:
    if not value:
        return "not set" if language == "en" else "не задано"
    maps = {
        "goal": GOAL_LABELS,
        "topic": TOPIC_LABELS,
        "correction": CORRECTION_LABELS,
        "reminder": REMINDER_LABELS,
        "language": LANGUAGE_LABELS,
        "voice": VOICE_LABELS,
    }
    return maps[kind][language].get(value, value)


def format_feedback(feedback: Feedback, language: str | None = "ru") -> str:
    phrases = "\n".join(
        f"- {item.original} -> {item.improved}" for item in feedback.improved_phrases
    )
    scores = "\n".join(f"- {item.name}: {item.score}/5 - {item.note}" for item in feedback.scores)
    if language == "en":
        return (
            "🧾 Session feedback\n"
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
    return (
        "🧾 Разбор сессии\n"
        "━━━━━━━━━━━━\n\n"
        f"📌 Итог: {feedback.summary}\n\n"
        f"✅ Сильная сторона: {feedback.main_strength}\n\n"
        f"🎯 Главная точка роста: {feedback.main_issue}\n\n"
        "💬 Фразы лучше:\n"
        f"{phrases}\n\n"
        f"🏠 Мини-задание: {feedback.micro_homework}\n\n"
        f"🏆 Примерный CEFR: {feedback.estimated_cefr}\n\n"
        "📊 Оценки:\n"
        f"{scores}"
    )


def format_profile(user: dict, progress: dict) -> str:
    language = language_of(user)
    completed = progress["completed_count"]
    display_name = user.get("first_name") or user.get("username") or (
        "User" if language == "en" else "Пользователь"
    )
    level = user.get("english_level") or "Not set"
    goal = label_value("goal", user.get("goal"), language)
    topics = ", ".join(
        label_value("topic", topic, language) for topic in user.get("topics", [])
    ) or ("not set" if language == "en" else "не задано")

    if completed == 0:
        if language == "en":
            return (
                f"👤 {display_name}\n\n"
                f"🏆 Level: {level}\n"
                "🔥 Sessions: 0\n"
                f"{format_streak(progress, language)}\n"
                f"📈 Progress: {progress_bar(0)} 0%\n\n"
                f"🎯 Goal: {goal}\n"
                f"📚 Topics: {topics}\n\n"
                "🚀 Start your first practice so dialogum can collect stats."
            )
        return (
            f"👤 {display_name}\n\n"
            f"🏆 Уровень: {level}\n"
            "🔥 Сессий: 0\n"
            f"{format_streak(progress, language)}\n"
            f"📈 Прогресс: {progress_bar(0)} 0%\n\n"
            f"🎯 Цель: {goal}\n"
            f"📚 Темы: {topics}\n\n"
            "🚀 Начни первую практику, чтобы dialogum собрал статистику."
        )

    feedback = progress.get("last_feedback") or {}
    cefr = feedback.get("estimated_cefr", "unknown")
    summary = progress.get("last_summary") or "No summary saved."
    percent = min(100, completed * 7)
    if language == "en":
        return (
            f"👤 {display_name}\n\n"
            f"🏆 Level: {cefr}\n"
            f"🔥 Sessions: {completed}\n"
            f"{format_streak(progress, language)}\n"
            f"📈 To next level: {progress_bar(percent)} {percent}%\n\n"
            f"🎯 Goal: {goal}\n"
            f"📚 Topics: {topics}\n\n"
            f"🧾 Last session: {summary}"
        )
    return (
        f"👤 {display_name}\n\n"
        f"🏆 Уровень: {cefr}\n"
        f"🔥 Сессий: {completed}\n"
        f"{format_streak(progress, language)}\n"
        f"📈 До следующего уровня: {progress_bar(percent)} {percent}%\n\n"
        f"🎯 Цель: {goal}\n"
        f"📚 Темы: {topics}\n\n"
        f"🧾 Последняя сессия: {summary}"
    )


def format_settings(user: dict) -> str:
    language = language_of(user)
    topics = ", ".join(
        label_value("topic", topic, language) for topic in user.get("topics", [])
    ) or ("not set" if language == "en" else "не задано")
    if language == "en":
        return (
            "⚙️ Settings\n"
            "━━━━━━━━━━━━\n\n"
            f"🏆 Level: {user.get('english_level') or 'not set'}\n"
            f"🎯 Goal: {label_value('goal', user.get('goal'), language)}\n"
            f"📚 Topics: {topics}\n"
            f"🧾 Corrections: {label_value('correction', user.get('correction_style'), language)}\n"
            f"🔔 Reminder: {label_value('reminder', user.get('reminder_time'), language)}\n"
            f"🔊 Bot voice: {label_value('voice', user.get('tts_voice') or 'en-US-JennyNeural', language)}\n"
            f"🌐 Interface: {label_value('language', user.get('interface_language'), language)}\n\n"
            "Choose what you want to change:"
        )
    return (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━\n\n"
        f"🏆 Уровень: {user.get('english_level') or 'not set'}\n"
        f"🎯 Цель: {label_value('goal', user.get('goal'), language)}\n"
        f"📚 Темы: {topics}\n"
        f"🧾 Исправления: {label_value('correction', user.get('correction_style'), language)}\n"
        f"🔔 Напоминание: {label_value('reminder', user.get('reminder_time'), language)}\n"
        f"🔊 Голос бота: {label_value('voice', user.get('tts_voice') or 'en-US-JennyNeural', language)}\n"
        f"🌐 Интерфейс: {label_value('language', user.get('interface_language'), language)}\n\n"
        "Выбери, что хочешь изменить:"
    )


def format_progress_insight(insight: ProgressInsight, language: str | None = "ru") -> str:
    if language == "en":
        achievements = "\n".join(f"- {item}" for item in insight.achievements) or "- Not enough data yet."
        return (
            "📈 Progress analysis\n"
            "━━━━━━━━━━━━\n\n"
            f"📌 Across sessions: {insight.overall_summary}\n\n"
            f"🔄 Recent change: {insight.recent_change}\n\n"
            f"🗓 Last 24 hours: {insight.last_day_summary}\n\n"
            "✅ Wins:\n"
            f"{achievements}\n\n"
            f"🎯 Next focus: {insight.next_focus}"
        )

    achievements = "\n".join(f"- {item}" for item in insight.achievements) or "- Пока мало данных."
    return (
        "📈 Анализ прогресса\n"
        "━━━━━━━━━━━━\n\n"
        f"📌 По сессиям: {insight.overall_summary}\n\n"
        f"🔄 Последнее изменение: {insight.recent_change}\n\n"
        f"🗓 За 24 часа: {insight.last_day_summary}\n\n"
        "✅ Что закрепилось:\n"
        f"{achievements}\n\n"
        f"🎯 Следующий фокус: {insight.next_focus}"
    )


def format_vocabulary(items: list[dict], language: str | None = "ru") -> str:
    if not items:
        if language == "en":
            return (
                "📚 Vocabulary\n"
                "━━━━━━━━━━━━\n\n"
                "No saved phrases yet. Finish a practice session to collect useful phrases."
            )
        return (
            "📚 Словарь\n"
            "━━━━━━━━━━━━\n\n"
            "Пока нет сохраненных фраз. Заверши практику, чтобы собрать полезные выражения."
        )

    lines = []
    for index, item in enumerate(items, start=1):
        phrase = item.get("phrase") or ""
        translation = item.get("translation") or ("no translation" if language == "en" else "без перевода")
        note = item.get("note") or ""
        times_seen = item.get("times_seen") or 1
        if note:
            lines.append(f"{index}. {phrase}\n   {translation}\n   {note} · x{times_seen}")
        else:
            lines.append(f"{index}. {phrase}\n   {translation} · x{times_seen}")

    title = "📚 Vocabulary" if language == "en" else "📚 Словарь"
    return f"{title}\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_topic_vocabulary(vocabulary: TopicVocabulary, language: str | None = "ru") -> str:
    title = "Words for this topic" if language == "en" else "Слова по теме"
    lines = []
    for index, item in enumerate(vocabulary.items, start=1):
        lines.append(
            f"{index}. {item.phrase}\n"
            f"   {item.translation}\n"
            f"   {item.example}"
        )
    return f"📚 {title}: {vocabulary.title}\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_skill_drill(drill: SkillDrill, language: str | None = "ru") -> str:
    title = "Targeted practice" if language == "en" else "Точечная тренировка"
    answer_label = "Answer" if language == "en" else "Ответ"
    lines = []
    for index, task in enumerate(drill.tasks, start=1):
        lines.append(
            f"{index}. {task.prompt}\n"
            f"{answer_label}: {task.answer}\n"
            f"{task.explanation}"
        )
    return f"🎯 {title}: {drill.title}\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_help(language: str | None = "ru") -> str:
    if language == "en":
        return (
            "📖 What can dialogum do?\n"
            "━━━━━━━━━━━━\n\n"
            "🎙 Gives you a short English speaking task.\n"
            "💬 Leads a short dialogue with follow-up questions.\n"
            "🧾 Shows mistakes and better phrases after the session.\n"
            "🧠 Remembers your goals, topics, and recurring weak spots.\n\n"
            "Format: 10 minutes a day, voice or text."
        )
    return (
        "📖 Что умеет dialogum?\n"
        "━━━━━━━━━━━━\n\n"
        "🎙 Дает короткое speaking-задание на английском.\n"
        "💬 Ведет диалог и задает уточняющие вопросы.\n"
        "🧾 После сессии показывает ошибки и улучшенные фразы.\n"
        "🧠 Запоминает цели, темы и типичные слабые места.\n\n"
        "Формат: 10 минут в день, voice или текст."
    )
