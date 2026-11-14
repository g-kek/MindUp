from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from mindup_bot.ai.roles import Evaluator, TopicSelector, Tutor
from mindup_bot.ai.schemas import TopicChoice, TutorReply
from mindup_bot.bot.handlers import fallback_feedback
from mindup_bot.db import Database
from mindup_bot.ielts import apply_ielts_flow, ensure_ielts_plan, next_ielts_prompt


def topic():
    return TopicChoice(
        topic_id="home",
        title="Home",
        opening_question="Where do you live?",
        rationale="Familiar topic",
    )


def session():
    plan = ensure_ielts_plan(topic())
    return {
        "topic_id": plan.topic_id,
        "topic_title": plan.title,
        "opening_question": plan.opening_question,
        "practice_mode": "ielts",
        "topic_plan": {
            key: getattr(plan, key)
            for key in ("second_question", "cue_card", "discussion_questions")
        },
    }


def test_five_answer_sequence_cannot_be_shortened_by_model():
    current = session()
    for turn, part in [(1, "Part 1"), (2, "Part 2"), (3, "Part 3"), (4, "Part 3")]:
        reply = apply_ielts_flow(TutorReply(reply="Thanks.", should_finish=True), current, turn)
        assert not reply.should_finish
        assert part in reply.follow_up
    assert "1 minute" in next_ielts_prompt(current, 2)
    assert "1–2 minutes" in next_ielts_prompt(current, 2)
    reply = apply_ielts_flow(
        TutorReply(reply="Thanks.", follow_up="One more?", should_finish=False), current, 5
    )
    assert reply.should_finish and reply.follow_up is None


@pytest.mark.asyncio
async def test_plan_and_turn_position_survive_database_reopen(tmp_path: Path):
    db = Database(tmp_path / "old.sqlite3")
    # Simulate a pre-upgrade database (sessions has no plan or practice_mode).
    async with db.connect() as connection:
        await connection.executescript("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                topic_id TEXT NOT NULL, topic_title TEXT NOT NULL, opening_question TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', turn_count INTEGER NOT NULL DEFAULT 0,
                summary TEXT, feedback_json TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT);
            INSERT INTO sessions(user_id, topic_id, topic_title, opening_question)
            VALUES (1, 'old', 'Old topic', 'Old question?');
        """)
        await connection.commit()
    await db.init()
    await db.init()  # Migrations must be safe to repeat.
    assert (await db.get_session(1))["practice_mode"] == "conversation"
    await db.upsert_user(2, 2, None, "Learner")
    plan = ensure_ielts_plan(topic())
    session_id = await db.create_session(2, plan.model_dump())
    await db.increment_turn_count(session_id)
    await db.increment_turn_count(session_id)
    reopened = await Database(db.path).get_active_session(2)
    assert reopened["turn_count"] == 2
    assert "Part 2" in next_ielts_prompt(reopened, reopened["turn_count"])
    assert reopened["topic_plan"]["cue_card"] == plan.cue_card


@pytest.mark.asyncio
async def test_tutor_uses_learning_history_and_respects_deferred_corrections():
    gateway = AsyncMock()
    gateway.generate_json.return_value = TutorReply(
        reply="Thank you.",
        soft_correction="I am ready",
        should_finish=True,
    )
    tutor = Tutor(gateway)
    reply = await tutor.respond(
        profile={"correction_style": "after_session", "learning_history": [{"rule_id": "verb_be"}]},
        session=session(),
        messages=[],
        user_message="I is ready",
        turn_number=2,
        min_turns=5,
        max_turns=5,
    )
    assert reply.soft_correction is None
    assert "Part 2" in reply.follow_up
    assert not reply.should_finish
    assert '"verb_be"' in gateway.generate_json.call_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_selector_populates_plan_and_evaluator_receives_history():
    gateway = AsyncMock()
    gateway.generate_json.return_value = topic()
    selected = await TopicSelector(gateway).select(profile={}, memories=[], recent_topics=[])
    assert selected.cue_card and len(selected.discussion_questions) == 2
    gateway.generate_json.return_value = fallback_feedback("en")
    await Evaluator(gateway).evaluate(
        profile={"learning_history": [{"rule_id": "articles", "error_sessions": 3}]},
        session=session(),
        messages=[],
        language="en",
    )
    prompt = gateway.generate_json.call_args.kwargs["prompt"]
    assert '"error_sessions": 3' in prompt
    assert "Practice mode: ielts" in prompt
