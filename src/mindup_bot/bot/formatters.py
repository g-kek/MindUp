from __future__ import annotations

from mindup_bot.ai.schemas import Feedback


def format_feedback(feedback: Feedback) -> str:
    phrases = "\n".join(
        f"- {item.original} -> {item.improved}" for item in feedback.improved_phrases
    )
    scores = "\n".join(f"- {item.name}: {item.score}/5 - {item.note}" for item in feedback.scores)
    return (
        "Session feedback\n\n"
        f"Summary: {feedback.summary}\n\n"
        f"Main strength: {feedback.main_strength}\n\n"
        f"Main issue: {feedback.main_issue}\n\n"
        "Better phrases:\n"
        f"{phrases}\n\n"
        f"Micro-homework: {feedback.micro_homework}\n\n"
        f"Estimated CEFR: {feedback.estimated_cefr}\n\n"
        "Scores:\n"
        f"{scores}"
    )


def format_progress(progress: dict) -> str:
    completed = progress["completed_count"]
    if completed == 0:
        return "No completed sessions yet. Start today's practice when you're ready."

    feedback = progress.get("last_feedback") or {}
    cefr = feedback.get("estimated_cefr", "unknown")
    summary = progress.get("last_summary") or "No summary saved."
    return (
        f"Completed sessions: {completed}\n"
        f"Last estimated CEFR: {cefr}\n\n"
        f"Last session: {summary}"
    )


def format_settings(user: dict) -> str:
    topics = ", ".join(user.get("topics") or []) or "not set"
    return (
        "Settings\n\n"
        f"Level: {user.get('english_level') or 'not set'}\n"
        f"Goal: {user.get('goal') or 'not set'}\n"
        f"Topics: {topics}\n"
        f"Corrections: {user.get('correction_style') or 'not set'}\n"
        f"Reminder: {user.get('reminder_time') or 'not set'}\n"
        f"Interface: {user.get('interface_language') or 'not set'}"
    )

