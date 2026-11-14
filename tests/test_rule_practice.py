from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from mindup_bot.ai.schemas import RuleAnswerEvaluation, RuleLesson
from mindup_bot.bot import handlers, rule_practice
from mindup_bot.bot.keyboards import RULE_PRACTICE_LABEL_EN
from mindup_bot.db import Database


def lesson() -> RuleLesson:
    return RuleLesson.model_validate(
        {
            "title": "Past Simple vs Present Perfect",
            "overview": "Compare a finished time and a present result.",
            "focus_rules": ["tenses"],
            "examples": [
                {
                    "sentence": "I lost my keys yesterday.",
                    "explanation": "A finished time: yesterday.",
                },
                {
                    "sentence": "I've lost my keys.",
                    "explanation": "The keys are still missing now.",
                },
            ],
            "tasks": [
                {
                    "kind": "choose",
                    "prompt": "Choose the form: Yesterday I ___ a hidden cafe.",
                    "choices": ["discovered", "have discovered"],
                    "correct_choice": 0,
                    "answer": "discovered",
                    "explanation": "Yesterday is a finished past time.",
                },
                {
                    "kind": "choose",
                    "prompt": "Choose the form for life experience, without a finished time: I ___ sushi before.",
                    "choices": ["have tried", "try"],
                    "correct_choice": 0,
                    "answer": "have tried",
                    "explanation": "An experience up to now.",
                },
                {
                    "kind": "gap",
                    "prompt": "Yesterday, I ___ (go) to a concert.",
                    "answer": "went",
                    "explanation": "Past Simple of go.",
                },
                {
                    "kind": "repair",
                    "prompt": "Correct: I have seen her yesterday.",
                    "answer": "I saw her yesterday.",
                    "explanation": "Use Past Simple with yesterday.",
                },
                {
                    "kind": "speaking",
                    "prompt": "Tell us about a trip: one finished event and one life experience.",
                    "answer": "I visited Rome in 2020. I have travelled to Italy twice.",
                    "explanation": "Use both forms with appropriate time contexts.",
                },
            ],
        }
    )


def grade(outcome="correct"):
    return RuleAnswerEvaluation(
        outcome=outcome,
        feedback="The time context is clear.",
        suggested_answer="I saw her yesterday.",
        next_hint="Notice finished time markers.",
    )


async def setup(tmp_path):
    db = Database(tmp_path / "rules.sqlite3")
    await db.init()
    await db.upsert_user(1, 10, "learner", "Learner")
    await db.complete_onboarding(1, {"english_level": "B1", "interface_language": "en"})
    coach = SimpleNamespace(
        build=AsyncMock(return_value=lesson()), check=AsyncMock(return_value=grade())
    )
    context = SimpleNamespace(
        args=[],
        application=SimpleNamespace(bot_data={"db": db, "rule_practice_coach": coach}),
        bot=AsyncMock(),
        user_data={},
    )
    message = SimpleNamespace(text=None, voice=None, reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, username="learner", first_name="Learner"),
        effective_chat=SimpleNamespace(id=10),
        effective_message=message,
        callback_query=None,
    )
    return db, coach, context, update


@pytest.mark.asyncio
async def test_full_training_via_menu_text_and_callbacks(tmp_path: Path):
    db, coach, context, update = await setup(tmp_path)
    update.effective_message.text = RULE_PRACTICE_LABEL_EN
    await handlers.handle_practice_message(update, context)
    assert (await db.get_user(1))["pending_action"] == "rule_topic"
    update.effective_message.text = "Past Simple vs Present Perfect"
    await handlers.handle_practice_message(update, context)
    active = await db.get_active_rule_practice(1)
    practice_id = active["id"]
    assert (await db.get_user(1))["pending_action"] == "rule_answer"
    # The task does not expose the correct_choice or its explanation before answering.
    task_call = update.effective_message.reply_text.call_args
    assert "Yesterday is a finished past time." not in task_call.args[0]
    assert [b.text for b in task_call.kwargs["reply_markup"].inline_keyboard[0]] == ["1", "2"]
    update.effective_message.text = "1"
    await handlers.handle_practice_message(update, context)
    coach.check.assert_not_awaited()  # A closed choice is checked deterministically.
    query = SimpleNamespace(
        message=update.effective_message, answer=AsyncMock(), data=f"train:answer:{practice_id}:1:1"
    )
    update.callback_query = query
    await handlers.handle_callback(update, context)
    assert (await db.get_active_rule_practice(1))["current_task"] == 2
    # Repeated clicks on an answered task cannot advance the next task.
    await handlers.handle_callback(update, context)
    assert (await db.get_active_rule_practice(1))["current_task"] == 2
    update.callback_query = None
    coach.check.side_effect = [grade(), grade("partial"), grade()]
    for text in (
        "went",
        "I saw her yesterday",
        "I went to Paris in 2023. I have visited France twice.",
    ):
        update.effective_message.text = text
        await handlers.handle_practice_message(update, context)
    assert await db.get_active_rule_practice(1) is None
    assert (await db.get_user(1))["pending_action"] is None
    attempts = await db.get_rule_attempts(practice_id, 1)
    assert [a["result"]["outcome"] for a in attempts] == [
        "correct",
        "incorrect",
        "correct",
        "partial",
        "correct",
    ]
    assert len(coach.check.call_args.kwargs["previous_attempts"]) == 4
    assert coach.check.call_args.kwargs["answer"].startswith("I went to Paris")
    history = await db.get_rule_practice_history(1)
    assert history[0]["correct"] == 3 and history[0]["attempted"] == 5
    # Prompted training does not falsely advance spontaneous speaking proficiency.
    assert await db.get_learning_profile(1) == []
    assert (await db.get_progress(1))["completed_count"] == 0
    assert any(
        "Training saved" in call.args[0]
        for call in update.effective_message.reply_text.call_args_list
    )


@pytest.mark.asyncio
async def test_check_failure_preserves_task_and_training_survives_restart(tmp_path: Path):
    db, coach, context, update = await setup(tmp_path)
    context.args = ["in/on/at"]
    await handlers.train_rule(update, context)
    active = await db.get_active_rule_practice(1)
    await db.record_rule_attempt(active["id"], 1, 0, "discovered", grade())
    await db.record_rule_attempt(active["id"], 1, 1, "have tried", grade())
    coach.check.side_effect = RuntimeError("AI unavailable")
    update.effective_message.text = "went"
    await handlers.handle_practice_message(update, context)
    assert len(await db.get_rule_attempts(active["id"], 1)) == 2
    assert (await db.get_active_rule_practice(1))["current_task"] == 2
    context.application.bot_data["db"] = Database(db.path)
    context.args = []
    await handlers.train_rule(update, context)
    assert "Task 3/5" in update.effective_message.reply_text.call_args.args[0]
    await handlers.finish(update, context)
    assert await db.get_active_rule_practice(1) is None
    assert len(await db.get_rule_attempts(active["id"], 1)) == 2


@pytest.mark.asyncio
async def test_creation_failure_retry_and_conflict_with_ielts(tmp_path: Path):
    db, coach, context, update = await setup(tmp_path)
    context.args = ["conditionals"]
    coach.build.side_effect = RuntimeError("AI unavailable")
    await handlers.train_rule(update, context)
    assert await db.get_active_rule_practice(1) is None
    assert (await db.get_user(1))["pending_action"] == "rule_topic"
    coach.build.side_effect = None
    update.effective_message.text = "conditionals"
    await handlers.handle_practice_message(update, context)
    active = await db.get_active_rule_practice(1)
    speaking_id = await db.create_session(
        1, {"topic_id": "home", "title": "Home", "opening_question": "Where do you live?"}
    )
    coach.build.reset_mock()
    await handlers.train_rule(update, context)
    coach.build.assert_not_awaited()
    assert (await db.get_active_rule_practice(1))["id"] == active["id"]
    with pytest.raises(ValueError, match="speaking session"):
        await db.create_rule_practice(1, "articles", lesson())
    assert (await db.get_active_session(1))["id"] == speaking_id


@pytest.mark.asyncio
async def test_training_callbacks_and_attempts_are_owner_scoped(tmp_path: Path):
    db, coach, context, update = await setup(tmp_path)
    practice_id = await db.create_rule_practice(1, "tenses", lesson())
    assert await db.get_rule_practice(practice_id, 2) is None
    assert await db.get_rule_attempts(practice_id, 2) == []
    assert not await db.record_rule_attempt(practice_id, 2, 0, "discovered", grade())
    assert not await db.stop_rule_practice(practice_id, 2)
    query = SimpleNamespace(message=update.effective_message, answer=AsyncMock())
    update.callback_query = query
    for callback in (f"train:answer:{practice_id}:0:0", f"train:stop:{practice_id}"):
        await rule_practice.callback(update, context, {"telegram_id": 2}, callback)
    assert (await db.get_active_rule_practice(1))["current_task"] == 0
    coach.check.assert_not_awaited()


@pytest.mark.asyncio
async def test_voice_answer_is_routed_to_training_not_ielts(tmp_path: Path, monkeypatch):
    db, coach, context, update = await setup(tmp_path)
    practice_id = await db.create_rule_practice(1, "tenses", lesson())
    await db.record_rule_attempt(practice_id, 1, 0, "discovered", grade())
    await db.record_rule_attempt(practice_id, 1, 1, "have tried", grade())
    update.effective_message.voice = SimpleNamespace()
    monkeypatch.setattr(handlers, "extract_user_text", AsyncMock(return_value="went"))
    await handlers.handle_practice_message(update, context)
    assert (await db.get_active_rule_practice(1))["current_task"] == 3
    assert coach.check.call_args.kwargs["answer"] == "went"


@pytest.mark.parametrize("change", ["duplicate_options", "wrong_answer", "no_contrast"])
def test_lesson_validation_rejects_ambiguous_structure(change):
    data = lesson().model_dump()
    if change == "duplicate_options":
        data["tasks"][0]["choices"] = ["discovered", "discovered"]
    elif change == "wrong_answer":
        data["tasks"][0]["answer"] = "have discovered"
    else:
        data["tasks"][1] = data["tasks"][2]
    with pytest.raises(ValidationError):
        RuleLesson.model_validate(data)


@pytest.mark.asyncio
async def test_finish_cancels_topic_prompt_and_new_topic_keeps_old_attempts(tmp_path: Path):
    db, _coach, context, update = await setup(tmp_path)
    await handlers.train_rule(update, context)
    assert (await db.get_user(1))["pending_action"] == "rule_topic"
    await handlers.finish(update, context)
    assert (await db.get_user(1))["pending_action"] is None
    first = await db.create_rule_practice(1, "tenses", lesson())
    await db.record_rule_attempt(first, 1, 0, "discovered", grade())
    second = await db.create_rule_practice(1, "articles", lesson())
    assert (await db.get_rule_practice(first, 1))["status"] == "cancelled"
    assert len(await db.get_rule_attempts(first, 1)) == 1
    assert (await db.get_active_rule_practice(1))["id"] == second
