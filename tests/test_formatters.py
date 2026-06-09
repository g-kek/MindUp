from mindup_bot.ai.schemas import Feedback, ProgressInsight, SkillDrill, TopicVocabulary
from mindup_bot.bot.formatters import (
    format_feedback,
    format_profile,
    format_progress_insight,
    format_processing_status,
    format_settings,
    format_skill_drill,
    format_skill_drill_card,
    format_topic_vocabulary,
    format_topic_vocabulary_card,
    format_vocabulary,
    format_vocabulary_card,
)


def test_format_feedback_contains_core_sections() -> None:
    feedback = Feedback.model_validate(
        {
            "summary": "You explained your opinion clearly.",
            "main_strength": "Clear basic structure.",
            "main_issue": "Needs more examples.",
            "improved_phrases": [
                {"original": "I think it good", "improved": "I think it is useful."},
                {"original": "People can to work", "improved": "People can work."},
            ],
            "micro_homework": "Give one example for each opinion.",
            "estimated_cefr": "B1",
            "scores": [
                {"name": "Clarity", "score": 4, "note": "Easy to follow."},
                {"name": "Vocabulary", "score": 3, "note": "Simple but enough."},
                {"name": "Grammar", "score": 3, "note": "Some errors."},
                {"name": "Argumentation", "score": 3, "note": "Could go deeper."},
            ],
        }
    )

    text = format_feedback(feedback)

    assert "<b>🧾 Разбор сессии</b>" in text
    assert "<b>Примерный CEFR:</b> B1" in text
    assert "<i>I think it good</i> → <b>I think it is useful.</b>" in text


def test_format_settings_uses_interface_language() -> None:
    user = {
        "english_level": "B1",
        "goal": "speaking_confidence",
        "topics": ["technology"],
        "correction_style": "after_session",
        "reminder_time": "none",
        "tts_voice": "en-US-GuyNeural",
        "interface_language": "en",
    }

    text = format_settings(user)

    assert "<b>⚙️ Settings</b>" in text
    assert "Speaking confidence" in text
    assert "Technology" in text
    assert "No reminders" in text
    assert "Guy · US male" in text
    assert "Настройки" not in text


def test_format_vocabulary_lists_saved_phrases() -> None:
    text = format_vocabulary(
        [
            {
                "phrase": "I tend to agree",
                "translation": "я скорее согласен",
                "note": "Useful soft opinion.",
                "times_seen": 2,
            }
        ],
        "ru",
    )

    assert "📚 Словарь" in text
    assert "I tend to agree" in text
    assert "я скорее согласен" in text
    assert "x2" in text

    card = format_vocabulary_card(
        [
            {
                "phrase": "I tend to agree",
                "translation": "я скорее согласен",
                "note": "Useful soft opinion.",
                "times_seen": 2,
            }
        ],
        0,
        "ru",
    )
    assert "1/1" not in card
    assert "<b>Заметка / пример:</b> Useful soft opinion." in card


def test_format_progress_insight_uses_language() -> None:
    insight = ProgressInsight(
        overall_summary="Ты стал увереннее отвечать.",
        recent_change="Ответы стали конкретнее.",
        last_day_summary="Вчера была одна сессия.",
        next_focus="Добавляй примеры.",
        achievements=["Регулярная практика"],
    )

    text = format_progress_insight(insight, "ru")

    assert "📈 Анализ прогресса" in text
    assert "Регулярная практика" in text


def test_format_profile_includes_daily_streak() -> None:
    user = {
        "first_name": "User",
        "english_level": "B1",
        "goal": "work",
        "topics": ["business"],
        "interface_language": "ru",
    }
    progress = {
        "completed_count": 2,
        "last_feedback": {"estimated_cefr": "B1"},
        "last_summary": "Короткая практика.",
        "streak": {"current": 3, "practiced_today": True},
    }

    text = format_profile(user, progress)

    assert "🔥 <b>Серия:</b> 3 дн. (сегодня выполнено)" in text


def test_format_topic_vocabulary_contains_examples() -> None:
    vocabulary = TopicVocabulary.model_validate(
        {
            "title": "Work focus",
            "items": [
                {
                    "phrase": "to stay focused",
                    "translation": "оставаться сфокусированным",
                    "example": "I try to stay focused in the morning.",
                },
                {
                    "phrase": "a clear priority",
                    "translation": "ясный приоритет",
                    "example": "I need a clear priority.",
                },
                {
                    "phrase": "to avoid distractions",
                    "translation": "избегать отвлечений",
                    "example": "I avoid distractions when I work.",
                },
                {
                    "phrase": "deep work",
                    "translation": "глубокая работа",
                    "example": "Deep work helps me finish difficult tasks.",
                },
                {
                    "phrase": "to plan ahead",
                    "translation": "планировать заранее",
                    "example": "I plan ahead on Sunday.",
                },
            ],
        }
    )

    text = format_topic_vocabulary(vocabulary, "ru")

    assert "📚 Слова и фразы по теме" in text
    assert "to stay focused" in text
    assert "I try to stay focused in the morning." in text

    card = format_topic_vocabulary_card(vocabulary, 0, "ru")
    assert "1/5" not in card
    assert "<b>Перевод:</b> оставаться сфокусированным" in card


def test_format_skill_drill_contains_tasks() -> None:
    drill = SkillDrill.model_validate(
        {
            "skill": "vocabulary",
            "title": "Vocabulary practice",
            "tasks": [
                {
                    "prompt": "Переведи: практичное решение.",
                    "answer": "a practical solution",
                    "explanation": "Useful phrase.",
                },
                {
                    "prompt": "Переведи: по моему опыту.",
                    "answer": "in my experience",
                    "explanation": "Use for examples.",
                },
                {
                    "prompt": "Закончи: This topic is important because ...",
                    "answer": "This topic is important because it affects people.",
                    "explanation": "Adds reason.",
                },
                {
                    "prompt": "Переведи: сравнить варианты.",
                    "answer": "to compare options",
                    "explanation": "Good for arguments.",
                },
                {
                    "prompt": "Составь фразу с clear example.",
                    "answer": "Let me give a clear example.",
                    "explanation": "Makes answer concrete.",
                },
            ],
        }
    )

    text = format_skill_drill(drill, "ru")

    assert "<b>🎯 Точечная тренировка" in text
    assert "<b>Ответ:</b> a practical solution" in text

    card = format_skill_drill_card(drill, 0, "ru")
    assert "<tg-spoiler>a practical solution</tg-spoiler>" in card
    assert "<b>Задание</b>" in card


def test_format_processing_status_has_progress_bar() -> None:
    text = format_processing_status(2, "ru")

    assert "<b>⏳ Обрабатываю сессию</b>" in text
    assert "▰▰▱▱" in text
