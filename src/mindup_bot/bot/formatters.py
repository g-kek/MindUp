from __future__ import annotations

from html import escape

from mindup_bot.ai.schemas import (
    Feedback,
    IELTSAssessment,
    LanguageError,
    ProgressInsight,
    SkillDrill,
    TopicVocabulary,
)
from mindup_bot.learning import IELTS_SOURCE, RULES, rule_label

GOAL_LABELS = {
    "ru": {
        "ielts": "IELTS Speaking",
        "work": "Работа",
        "travel": "Путешествия",
        "study": "Учеба",
        "interviews": "Собеседования",
        "speaking_confidence": "Уверенность в речи",
        "thinking_self_expression": "Мышление и самовыражение",
    },
    "en": {
        "ielts": "IELTS Speaking",
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
        return f"🔥 <b>Streak:</b> {current} days ({escape(status)})"
    status = "сегодня выполнено" if practiced_today else "сегодня еще нет"
    return f"🔥 <b>Серия:</b> {current} дн. ({escape(status)})"


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


def _value(value: object) -> str:
    return escape(str(value or ""))


def _label(label: str, value: object) -> str:
    return f"<b>{escape(label)}:</b> {_value(value)}"


def format_feedback(feedback: Feedback, language: str | None = "ru") -> str:
    if not feedback.analysis_available:
        return ("<b>🧾 Session feedback</b>\n\n" if language == "en" else
                "<b>🧾 Разбор сессии</b>\n\n") + _value(feedback.summary)
    phrases = "\n".join(
        f"• <i>{_value(item.original)}</i> → <b>{_value(item.improved)}</b>"
        for item in feedback.improved_phrases
    )
    scores = "\n".join(
        f"• <b>{_value(item.name)}:</b> {item.score}/5 - {_value(item.note)}"
        for item in feedback.scores
    )
    if language == "en":
        return (
            "<b>🧾 Session feedback</b>\n"
            "━━━━━━━━━━━━\n\n"
            f"📌 {_label('Summary', feedback.summary)}\n\n"
            f"✅ {_label('Main strength', feedback.main_strength)}\n\n"
            f"🎯 {_label('Main issue', feedback.main_issue)}\n\n"
            "<b>💬 Better phrases</b>\n"
            f"{phrases}\n\n"
            f"🏠 {_label('Micro-homework', feedback.micro_homework)}\n\n"
            f"🏆 {_label('Estimated CEFR', feedback.estimated_cefr)}\n\n"
            "<b>📊 Scores</b>\n"
            f"{scores}"
        )
    return (
        "<b>🧾 Разбор сессии</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"📌 {_label('Итог', feedback.summary)}\n\n"
        f"✅ {_label('Сильная сторона', feedback.main_strength)}\n\n"
        f"🎯 {_label('Главная точка роста', feedback.main_issue)}\n\n"
        "<b>💬 Фразы лучше</b>\n"
        f"{phrases}\n\n"
        f"🏠 {_label('Мини-задание', feedback.micro_homework)}\n\n"
        f"🏆 {_label('Примерный CEFR', feedback.estimated_cefr)}\n\n"
        "<b>📊 Оценки</b>\n"
        f"{scores}"
    )


def format_language_error(error: LanguageError, language: str | None = "ru") -> str:
    en = language == "en"
    labels = (
        ["Rule", "Possible cause (hypothesis)", "Evidence / uncertainty", "Next step"]
        if en
        else [
            "Правило",
            "Возможная причина (гипотеза)",
            "Наблюдение / неопределённость",
            "Как отработать",
        ]
    )
    source = "Reference" if en else "Справочник"
    if error.rule_id in {"collocations", "idioms", "word_choice"}:
        source += " · Cambridge Grammar"
    else:
        source += " · British Council"
    return (
        f"<b>🔎 {_value(rule_label(error.rule_id, language))}</b>\n\n"
        f"<i>{_value(error.original)}</i> → <b>{_value(error.corrected)}</b>\n\n"
        f"{_label(labels[0], error.explanation)}\n\n"
        f"{_label(labels[1], error.likely_cause)}\n"
        f"{_label(labels[2], error.cause_evidence)}\n\n"
        f"{_label(labels[3], error.next_step)}\n\n"
        f'<a href="{escape(RULES[error.rule_id][2], quote=True)}">{source}</a>'
    )


def format_ielts_assessment(assessment: IELTSAssessment, language: str | None = "ru") -> str:
    en = language == "en"
    limitation = (
        "Pronunciation and spoken fluency are not assessed from a transcript. "
        "These are practice notes, not an official band score."
        if en
        else "По расшифровке нельзя оценить произношение и беглость речи. "
        "Это учебный разбор, без общего балла IELTS."
    )
    return (
        "<b>IELTS Speaking</b>\n\n"
        + _label("Coherence" if en else "Связность", assessment.coherence)
        + "\n\n"
        + _label("Lexical resource" if en else "Лексика", assessment.lexical_resource)
        + "\n\n"
        + _label(
            "Grammar" if en else "Грамматический диапазон и точность",
            assessment.grammatical_range_accuracy,
        )
        + "\n\n"
        + limitation
        + f'\n<a href="{IELTS_SOURCE}">IELTS · Speaking criteria</a>'
    )


def format_learning_profile(history: list[dict], language: str | None = "ru") -> str:
    en = language == "en"
    title = "Observed learning patterns" if en else "Наблюдения по твоей речи"
    parts = [f"<b>🎯 {title}</b>"]
    if not history:
        parts.append(
            "Not enough rule evidence yet. Complete a new practice."
            if en
            else "Пока нет наблюдений по правилам. Заверши новую практику."
        )
        return "\n\n".join(parts)
    statuses = (
        {
            "recurring": "Repeating",
            "needs_practice": "Needs practice",
            "improving": "Improving",
            "stabilizing": "Becoming consistent",
            "observed": "Correct usage observed",
        }
        if en
        else {
            "recurring": "Повторяется",
            "needs_practice": "Нужно отработать",
            "improving": "Есть улучшение",
            "stabilizing": "Закрепляется",
            "observed": "Есть верное применение",
        }
    )
    for item in history:
        rule = rule_label(item["rule_id"], language)
        counts = (
            f"errors in {item['error_sessions']}/{item['observed_sessions']} observed sessions"
            if en
            else f"ошибки в {item['error_sessions']}/{item['observed_sessions']} сессий с примерами"
        )
        streak = (
            (
                f"; {item['clean_streak']} correct in a row"
                if en
                else f"; верно подряд: {item['clean_streak']}"
            )
            if item["clean_streak"]
            else ""
        )
        parts.append(f"• <b>{_value(rule)}</b>: {statuses[item['status']]}\n{counts}{streak}")
    target = next((item for item in history if item["error_sessions"]), None)
    if target:
        parts.append(
            _label(
                "Next focus" if en else "Следующий фокус", rule_label(target["rule_id"], language)
            )
        )
        parts.append(_label("Example" if en else "Пример", target["example"]))
        next_step = target.get("details", {}).get("next_step")
        if next_step:
            parts.append(_value(next_step))
    parts.append(
        "Only observed uses count; silence does not prove improvement."
        if en
        else "Учитываются только примеры применения. Отсутствие ошибки ещё не доказывает прогресс."
    )
    return "\n\n".join(parts)


def format_rule_practice_history(history: list[dict], language: str | None = "ru") -> str:
    en = language == "en"
    title = "Recent rule training" if en else "Последние тренировки правил"
    lines = [f"<b>🧩 {title}</b>"]
    for practice in history:
        counts = f"{practice['correct']}/{practice['attempted']}"
        label = "correct on first attempt" if en else "верно с первой попытки"
        lines.append(f"• {_value(practice['requested_topic'])}: {counts} {label}")
    lines.append(
        "These are prompted exercises; speaking progress is tracked separately."
        if en
        else "Это упражнения с подсказками; прогресс в свободной речи учитывается отдельно."
    )
    return "\n\n".join(lines)


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
                f"<b>👤 {_value(display_name)}</b>\n\n"
                f"🏆 {_label('Level', level)}\n"
                f"🔥 {_label('Sessions', 0)}\n"
                f"{format_streak(progress, language)}\n"
                f"🎯 {_label('Goal', goal)}\n"
                f"📚 {_label('Topics', topics)}\n\n"
                "🚀 Start your first practice so dialogum can collect stats."
            )
        return (
            f"<b>👤 {_value(display_name)}</b>\n\n"
            f"🏆 {_label('Уровень', level)}\n"
            f"🔥 {_label('Сессий', 0)}\n"
            f"{format_streak(progress, language)}\n"
            f"🎯 {_label('Цель', goal)}\n"
            f"📚 {_label('Темы', topics)}\n\n"
            "🚀 Начни первую практику, чтобы dialogum собрал статистику."
        )

    feedback = progress.get("last_feedback") or {}
    cefr = feedback.get("estimated_cefr") if feedback.get("analysis_available", True) else None
    cefr = cefr or level
    summary = progress.get("last_summary") or "No summary saved."
    if language == "en":
        return (
            f"<b>👤 {_value(display_name)}</b>\n\n"
            f"🏆 {_label('Level', cefr)}\n"
            f"🔥 {_label('Sessions', completed)}\n"
            f"{format_streak(progress, language)}\n"
            f"🎯 {_label('Goal', goal)}\n"
            f"📚 {_label('Topics', topics)}\n\n"
            f"🧾 {_label('Last session', summary)}"
        )
    return (
        f"<b>👤 {_value(display_name)}</b>\n\n"
        f"🏆 {_label('Уровень', cefr)}\n"
        f"🔥 {_label('Сессий', completed)}\n"
        f"{format_streak(progress, language)}\n"
        f"🎯 {_label('Цель', goal)}\n"
        f"📚 {_label('Темы', topics)}\n\n"
        f"🧾 {_label('Последняя сессия', summary)}"
    )


def format_settings(user: dict) -> str:
    language = language_of(user)
    topics = ", ".join(
        label_value("topic", topic, language) for topic in user.get("topics", [])
    ) or ("not set" if language == "en" else "не задано")
    if language == "en":
        return (
            "<b>⚙️ Settings</b>\n"
            "━━━━━━━━━━━━\n\n"
            f"🏆 {_label('Level', user.get('english_level') or 'not set')}\n"
            f"🎯 {_label('Goal', label_value('goal', user.get('goal'), language))}\n"
            f"📚 {_label('Topics', topics)}\n"
            f"🧾 {_label('Corrections', label_value('correction', user.get('correction_style'), language))}\n"
            f"🔔 {_label('Reminder', label_value('reminder', user.get('reminder_time'), language))}\n"
            f"🔊 {_label('Bot voice', label_value('voice', user.get('tts_voice') or 'en-US-JennyNeural', language))}\n"
            f"🌐 {_label('Interface', label_value('language', user.get('interface_language'), language))}\n\n"
            "Choose what you want to change:"
        )
    return (
        "<b>⚙️ Настройки</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"🏆 {_label('Уровень', user.get('english_level') or 'not set')}\n"
        f"🎯 {_label('Цель', label_value('goal', user.get('goal'), language))}\n"
        f"📚 {_label('Темы', topics)}\n"
        f"🧾 {_label('Исправления', label_value('correction', user.get('correction_style'), language))}\n"
        f"🔔 {_label('Напоминание', label_value('reminder', user.get('reminder_time'), language))}\n"
        f"🔊 {_label('Голосовые сообщения', label_value('voice', user.get('tts_voice') or 'en-US-JennyNeural', language))}\n"
        f"🌐 {_label('Интерфейс', label_value('language', user.get('interface_language'), language))}\n\n"
        "Выбери, что хочешь изменить:"
    )


def format_progress_insight(insight: ProgressInsight, language: str | None = "ru") -> str:
    if language == "en":
        achievements = "\n".join(f"• {_value(item)}" for item in insight.achievements) or "• Not enough data yet."
        return (
            "<b>📈 Progress analysis</b>\n"
            "━━━━━━━━━━━━\n\n"
            f"📌 {_label('Across sessions', insight.overall_summary)}\n\n"
            f"🔄 {_label('Recent change', insight.recent_change)}\n\n"
            f"🗓 {_label('Last 24 hours', insight.last_day_summary)}\n\n"
            "<b>✅ Wins</b>\n"
            f"{achievements}\n\n"
            f"🎯 {_label('Next focus', insight.next_focus)}"
        )

    achievements = "\n".join(f"• {_value(item)}" for item in insight.achievements) or "• Пока мало данных."
    return (
        "<b>📈 Анализ прогресса</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"📌 {_label('По сессиям', insight.overall_summary)}\n\n"
        f"🔄 {_label('Последнее изменение', insight.recent_change)}\n\n"
        f"🗓 {_label('За 24 часа', insight.last_day_summary)}\n\n"
        "<b>✅ Что закрепилось</b>\n"
        f"{achievements}\n\n"
        f"🎯 {_label('Следующий фокус', insight.next_focus)}"
    )


def format_vocabulary(items: list[dict], language: str | None = "ru") -> str:
    if not items:
        if language == "en":
            return (
                "<b>📚 Vocabulary</b>\n"
                "━━━━━━━━━━━━\n\n"
                "No saved phrases yet. Finish a practice session to collect useful phrases."
            )
        return (
            "<b>📚 Словарь</b>\n"
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
            lines.append(
                f"<b>{index}. {_value(phrase)}</b>\n"
                f"{_label('Перевод' if language != 'en' else 'Translation', translation)}\n"
                f"{_label('Заметка' if language != 'en' else 'Note', note)} · x{times_seen}"
            )
        else:
            lines.append(
                f"<b>{index}. {_value(phrase)}</b>\n"
                f"{_label('Перевод' if language != 'en' else 'Translation', translation)} · x{times_seen}"
            )

    title = "📚 Vocabulary" if language == "en" else "📚 Словарь"
    return f"<b>{escape(title)}</b>\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_vocabulary_card(items: list[dict], page: int, language: str | None = "ru") -> str:
    if not items:
        return format_vocabulary(items, language)

    safe_page = _safe_page(page, len(items))
    item = items[safe_page]
    phrase = item.get("phrase") or ""
    translation = item.get("translation") or ("no translation" if language == "en" else "без перевода")
    note = item.get("note") or ""
    times_seen = item.get("times_seen") or 1
    title = "📚 Vocabulary" if language == "en" else "📚 Словарь"
    translation_label = "Translation" if language == "en" else "Перевод"
    note_label = "Note / example" if language == "en" else "Заметка / пример"
    seen_label = "Seen" if language == "en" else "Повторений"

    parts = [
        f"<b>{escape(title)}</b>\n━━━━━━━━━━━━",
        f"<b>{_value(phrase)}</b>",
        _label(translation_label, translation),
    ]
    if note:
        parts.append(_label(note_label, note))
    parts.append(_label(seen_label, f"x{times_seen}"))
    return "\n\n".join(parts)


def format_topic_vocabulary(vocabulary: TopicVocabulary, language: str | None = "ru") -> str:
    title = "Words and phrases for this topic" if language == "en" else "Слова и фразы по теме"
    lines = []
    for index, item in enumerate(vocabulary.items, start=1):
        lines.append(
            f"<b>{index}. {_value(item.phrase)}</b>\n"
            f"{_label('Перевод' if language != 'en' else 'Translation', item.translation)}\n"
            f"{_label('Пример' if language != 'en' else 'Example', item.example)}"
        )
    return f"<b>📚 {escape(title)}: {_value(vocabulary.title)}</b>\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_topic_vocabulary_card(
    vocabulary: TopicVocabulary,
    page: int,
    language: str | None = "ru",
) -> str:
    safe_page = _safe_page(page, len(vocabulary.items))
    item = vocabulary.items[safe_page]
    title = "Words and phrases for this topic" if language == "en" else "Слова и фразы по теме"
    translation_label = "Translation" if language == "en" else "Перевод"
    example_label = "Example" if language == "en" else "Пример"
    return (
        f"<b>📚 {escape(title)}: {_value(vocabulary.title)}</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"<b>{_value(item.phrase)}</b>\n\n"
        f"{_label(translation_label, item.translation)}\n\n"
        f"{_label(example_label, item.example)}"
    )


def format_skill_drill(drill: SkillDrill, language: str | None = "ru") -> str:
    title = "Targeted practice" if language == "en" else "Точечная тренировка"
    answer_label = "Answer" if language == "en" else "Ответ"
    lines = []
    for index, task in enumerate(drill.tasks, start=1):
        lines.append(
            f"<b>{index}. {_value(task.prompt)}</b>\n"
            f"{_label(answer_label, task.answer)}\n"
            f"{_value(task.explanation)}"
        )
    return f"<b>🎯 {escape(title)}: {_value(drill.title)}</b>\n━━━━━━━━━━━━\n\n" + "\n\n".join(lines)


def format_skill_drill_card(drill: SkillDrill, page: int, language: str | None = "ru") -> str:
    safe_page = _safe_page(page, len(drill.tasks))
    task = drill.tasks[safe_page]
    title = "Targeted practice" if language == "en" else "Точечная тренировка"
    prompt_label = "Task" if language == "en" else "Задание"
    answer_label = "Tap to reveal the answer" if language == "en" else "Нажми, чтобы открыть ответ"
    explanation_label = "Why it works" if language == "en" else "Почему так"
    return (
        f"<b>🎯 {escape(title)}: {escape(drill.title)}</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"<b>{escape(prompt_label)}</b>\n"
        f"{escape(task.prompt)}\n\n"
        f"<b>{escape(answer_label)}</b>\n"
        f"<tg-spoiler>{escape(task.answer)}</tg-spoiler>\n\n"
        f"<b>{escape(explanation_label)}</b>\n"
        f"{escape(task.explanation)}"
    )


def format_short_session_warning(language: str | None = "ru") -> str:
    if language == "en":
        return (
            "<b>🟡 Not enough dialogue yet</b>\n"
            "━━━━━━━━━━━━\n\n"
            "Send at least two messages in this speaking session so I can make a useful analysis.\n\n"
            "<b>You can still finish now</b>, but I will close the session without feedback, vocabulary, or drills."
        )
    return (
        "<b>🟡 Пока мало диалога</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Отправь хотя бы два сообщения в этой speaking-сессии, чтобы я смог сделать полезный разбор.\n\n"
        "<b>Можно завершить сейчас</b>, но тогда сессия закроется без анализа, словаря и тренировки."
    )


def format_no_analysis_finished(language: str | None = "ru") -> str:
    if language == "en":
        return (
            "<b>✅ Session closed</b>\n"
            "━━━━━━━━━━━━\n\n"
            "Analysis was skipped because there were fewer than two user messages."
        )
    return (
        "<b>✅ Сессия закрыта</b>\n"
        "━━━━━━━━━━━━\n\n"
        "Анализ пропущен: в сессии было меньше двух сообщений пользователя."
    )


def format_processing_status(step: int, language: str | None = "ru") -> str:
    safe_step = max(1, min(step, 4))
    bar = "▰" * safe_step + "▱" * (4 - safe_step)
    if language == "en":
        labels = {
            1: "Reading the dialogue",
            2: "Analyzing speaking quality",
            3: "Saving useful phrases",
            4: "Preparing the result",
        }
        return (
            "<b>⏳ Processing your session</b>\n"
            "━━━━━━━━━━━━\n\n"
            f"{bar}\n"
            f"{labels[safe_step]}..."
        )
    labels = {
        1: "Читаю диалог",
        2: "Анализирую речь",
        3: "Сохраняю полезные фразы",
        4: "Готовлю результат",
    }
    return (
        "<b>⏳ Обрабатываю сессию</b>\n"
        "━━━━━━━━━━━━\n\n"
        f"{bar}\n"
        f"{labels[safe_step]}..."
    )


def format_help(language: str | None = "ru") -> str:
    if language == "en":
        return (
            "<b>📖 What can dialogum do?</b>\n"
            "━━━━━━━━━━━━\n\n"
            "🎙 <b>/ielts:</b> shortened IELTS Speaking Parts 1–3, five answers.\n"
            "💬 <b>Dialogue:</b> leads a short conversation with follow-up questions.\n"
            "🧾 <b>Feedback:</b> shows mistakes and better phrases after the session.\n"
            "🧠 <b>/progress:</b> recurring errors, observed improvements and next focus.\n"
            "🧩 <b>/train rule or topic:</b> contrasts, examples and five checked exercises.\n"
            "📚 <b>/vocabulary</b> and <b>/review:</b> phrases and revision.\n\n"
            "<b>Format:</b> 10 minutes a day, voice or text."
        )
    return (
        "<b>📖 Что умеет dialogum?</b>\n"
        "━━━━━━━━━━━━\n\n"
        "🎙 <b>/ielts:</b> короткая практика IELTS Speaking Parts 1–3, пять ответов.\n"
        "💬 <b>Диалог:</b> ведет разговор и задает уточняющие вопросы.\n"
        "🧾 <b>Разбор:</b> после сессии показывает ошибки и улучшенные фразы.\n"
        "🧠 <b>/progress:</b> повторяющиеся ошибки, улучшения и следующий фокус.\n"
        "🧩 <b>/train правило или тема:</b> сравнения, примеры и пять заданий с проверкой.\n"
        "📚 <b>/vocabulary</b> и <b>/review:</b> фразы и повторение.\n\n"
        "<b>Формат:</b> 10 минут в день, голосовое сообщение или текст."
    )


def _safe_page(page: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(max(page, 0), total - 1)
