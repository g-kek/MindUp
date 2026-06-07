from mindup_bot.ai.schemas import Feedback
from mindup_bot.bot.formatters import format_feedback


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
    assert "🏆 Estimated CEFR: B1" in text
    assert "I think it good -> I think it is useful." in text
