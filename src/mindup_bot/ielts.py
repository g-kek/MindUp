"""Deterministic shortened IELTS Speaking practice (not a timed full mock exam)."""

from __future__ import annotations

from typing import Any

from mindup_bot.ai.schemas import TopicChoice, TutorReply

IELTS_TURNS = 5


def ensure_ielts_plan(topic: TopicChoice) -> TopicChoice:
    topic.practice_mode = "ielts"
    topic.second_question = (
        topic.second_question or "Has your experience of this changed over time?"
    )
    topic.cue_card = topic.cue_card or (
        f"Describe a memorable experience related to {topic.title}.\n"
        "You should say:\n• when and where it happened\n• who was involved\n"
        "• what happened\nand explain why it was memorable."
    )
    topic.discussion_questions = [q.strip()[:400] for q in topic.discussion_questions if q.strip()]
    if len(topic.discussion_questions) != 2:
        topic.discussion_questions = [
            f"How has the role of {topic.title} in society changed compared with the past?",
            f"What changes related to {topic.title} might we see in the future, and why?",
        ]
    return topic


def next_ielts_prompt(session: dict[str, Any], turn_number: int) -> str | None:
    plan = ensure_ielts_plan(
        TopicChoice(
            topic_id=session["topic_id"],
            title=session["topic_title"],
            opening_question=session["opening_question"],
            rationale="",
            **session.get("topic_plan", {}),
        )
    )
    if turn_number == 1:
        return "IELTS Speaking · Part 1\n" + plan.second_question
    if turn_number == 2:
        return (
            "IELTS Speaking · Part 2\nPrepare for 1 minute, then speak for 1–2 minutes.\n\n"
            + plan.cue_card
        )
    if turn_number in (3, 4):
        return "IELTS Speaking · Part 3\n" + plan.discussion_questions[turn_number - 3]
    return None


def apply_ielts_flow(reply: TutorReply, session: dict[str, Any], turn_number: int) -> TutorReply:
    if session.get("practice_mode") == "ielts":
        reply.follow_up = next_ielts_prompt(session, turn_number)
        reply.should_finish = turn_number >= IELTS_TURNS
    return reply
