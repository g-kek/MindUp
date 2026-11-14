from pathlib import Path

import pytest

from mindup_bot.ai.schemas import CorrectUsage, ImprovedPhrase, LanguageError
from mindup_bot.bot.formatters import format_language_error, format_learning_profile, format_profile
from mindup_bot.bot.handlers import fallback_feedback, fallback_skill_drill
from mindup_bot.db import Database
from mindup_bot.learning import RULES, grounded_feedback, learning_profile


def error(**updates) -> LanguageError:
    return LanguageError(
        **{
            "rule_id": "verb_be",
            "original": "I is ready",
            "corrected": "I am ready",
            "explanation": "Use am with I.",
            "likely_cause": "Possibly an unpractised agreement pattern; too little evidence yet.",
            "cause_evidence": "One example: I is ready.",
            "next_step": "Contrast I am ready with she is ready, then give a personal example.",
            **updates,
        }
    )


def feedback(**updates):
    return fallback_feedback("en").model_copy(update={"analysis_available": True, **updates})


def test_grounding_rejects_invented_tutor_and_unclear_quotes():
    assessment = feedback(
        errors=[
            error(),
            error(),
            error(original="She are ready"),
            error(original="I is [unclear]"),
        ],
        correct_usage=[
            CorrectUsage(rule_id="verb_be", quote="I am ready"),
            CorrectUsage(rule_id="verb_be", quote="I is ready"),
        ],
        improved_phrases=[ImprovedPhrase(original="She are ready", improved="She is ready")],
    )
    checked = grounded_feedback(
        assessment,
        [
            {"role": "user", "content": "I is ready"},
            {"role": "tutor", "content": "She are ready"},
            {"role": "user", "content": "I am ready [unclear]"},
        ],
    )
    assert len(checked.errors) == 1
    assert checked.correct_usage == []
    assert checked.improved_phrases == []


def row(session_id, outcome="error", rule_id="verb_be"):
    return {
        "session_id": session_id,
        "rule_id": rule_id,
        "outcome": outcome,
        "quote": "I is ready" if outcome == "error" else "I am ready",
        "completed_at": f"2026-11-{session_id:02d} 12:00:00",
        "details": {},
    }


def test_progress_requires_observed_correct_uses_in_separate_sessions():
    rows = [row(1), row(1), row(2)]
    recurring = learning_profile(rows)[0]
    assert recurring["status"] == "recurring"
    assert recurring["error_sessions"] == 2
    # Other rules and sessions with no relevant example cannot establish progress.
    assert learning_profile(rows + [row(3, "correct", "articles")])[0]["status"] == "recurring"
    assert learning_profile(rows + [row(3, "correct")])[0]["status"] == "recurring"
    assert (
        learning_profile(rows + [row(3, "correct"), row(4, "correct")])[0]["status"] == "improving"
    )
    assert (
        learning_profile(rows + [row(3, "correct"), row(4, "correct"), row(5, "correct")])[0][
            "status"
        ]
        == "stabilizing"
    )
    assert learning_profile(rows + [row(3, "correct"), row(3, "error")])[0]["clean_streak"] == 0


@pytest.mark.asyncio
async def test_completion_is_atomic_grounded_idempotent_and_user_scoped(tmp_path: Path):
    db = Database(tmp_path / "bot.sqlite3")
    await db.init()
    await db.upsert_user(1, 1, None, "Learner")
    await db.upsert_user(2, 2, None, "Other")
    topic = {"topic_id": "home", "title": "Home", "opening_question": "Where do you live?"}
    session_id = await db.create_session(1, topic)
    await db.add_message(session_id, "user", "I is ready")
    await db.add_message(session_id, "tutor", "She are ready")
    assessment = feedback(errors=[error(), error(original="She are ready")])
    await db.complete_session(session_id, assessment.summary, assessment.model_dump())
    await db.complete_session(session_id, "Repeated", feedback().model_dump())
    history = await db.get_learning_profile(1)
    assert len(history) == 1
    assert history[0]["observed_sessions"] == 1
    assert await db.get_learning_profile(2) == []
    persisted = await db.get_session(session_id)
    assert len(persisted["feedback"]["errors"]) == 1
    assert persisted["summary"] == assessment.summary
    # Reopen the file: evidence survives process restart.
    assert await Database(db.path).get_learning_profile(1) == history
    failed_id = await db.create_session(1, topic)
    await db.add_message(failed_id, "user", "I is ready")
    await db.complete_session(failed_id, "Unavailable", fallback_feedback().model_dump())
    assert await db.get_learning_profile(1) == history


def test_rule_card_is_safe_and_links_to_curated_source():
    card = format_language_error(
        error(likely_cause='<a href="https://evil.example">test</a>'), "ru"
    )
    assert "гипотеза" in card
    assert "&lt;a href=" in card
    assert f'href="{RULES["verb_be"][2]}"' in card
    assert "I is ready" in card and "I am ready" in card
    assert len(card) < 4096


def test_rule_fallback_drill_uses_actual_error_and_does_not_create_learning_evidence():
    drill = fallback_skill_drill({}, "verb_be", "en", feedback=feedback(errors=[error()]))
    assert len(drill.tasks) == 5
    assert drill.tasks[0].prompt.endswith("I is ready")
    assert all(task.answer == "I am ready" for task in drill.tasks)


def test_profile_reports_evidence_without_session_count_level_claim():
    user = {"first_name": "Learner", "english_level": "B1", "interface_language": "en"}
    profile = format_profile(user, {"completed_count": 100, "last_feedback": {}})
    assert "%" not in profile
    report = format_learning_profile(learning_profile([row(1), row(2)]), "en")
    assert "Repeating" in report and "2/2" in report
    assert "I is ready" in report
    assert "silence" in report


def test_unavailable_feedback_has_no_fabricated_scores_or_quotes():
    assessment = fallback_feedback("en")
    assert not assessment.analysis_available
    assert not assessment.scores and not assessment.errors and not assessment.improved_phrases
