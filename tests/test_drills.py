from mindup_bot.ai.schemas import Feedback
from mindup_bot.bot.handlers import fallback_skill_drill, skill_slug_for, weakest_feedback_score


def test_weakest_feedback_score_and_skill_slug() -> None:
    feedback = Feedback.model_validate(
        {
            "summary": "Done.",
            "main_strength": "Clear enough.",
            "main_issue": "Vocabulary needs work.",
            "improved_phrases": [
                {"original": "good thing", "improved": "useful solution"},
                {"original": "I think yes", "improved": "I tend to agree"},
            ],
            "micro_homework": "Practice phrases.",
            "estimated_cefr": "B1",
            "scores": [
                {"name": "Clarity", "score": 4, "note": "Good."},
                {"name": "Vocabulary", "score": 2, "note": "Needs more range."},
                {"name": "Grammar patterns", "score": 3, "note": "Some issues."},
                {"name": "Communicative ability", "score": 3, "note": "OK."},
            ],
        }
    )

    weak_score = weakest_feedback_score(feedback)

    assert weak_score is not None
    assert weak_score.name == "Vocabulary"
    assert skill_slug_for(weak_score.name) == "vocabulary"


def test_fallback_skill_drill_has_five_tasks() -> None:
    drill = fallback_skill_drill(
        {
            "topic_title": "Work focus",
            "opening_question": "What helps you focus at work?",
        },
        "grammar_patterns",
        "ru",
    )

    assert drill.skill == "grammar patterns"
    assert len(drill.tasks) == 5
    assert drill.tasks[0].answer
