from mindup_bot.ai.schemas import Feedback, ProgressInsight
from mindup_bot.bot.formatters import (
    format_feedback,
    format_progress_insight,
    format_settings,
    format_vocabulary,
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

    assert "🧾 Разбор сессии" in text
    assert "🏆 Примерный CEFR: B1" in text
    assert "I think it good -> I think it is useful." in text


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

    assert "⚙️ Settings" in text
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
