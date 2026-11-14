"""Offline integration of Telegram handlers, AI roles and the real SQLite store."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindup_bot.ai.roles import Evaluator, MemoryUpdater, TopicSelector, Tutor, VocabularyExtractor
from mindup_bot.ai.schemas import (
    Feedback,
    LanguageError,
    MemoryUpdate,
    TopicChoice,
    TutorReply,
    VocabularyUpdate,
)
from mindup_bot.bot import handlers
from mindup_bot.db import Database


def assessment() -> Feedback:
    return Feedback(
        summary="One agreement error.",
        main_strength="A clear answer.",
        main_issue="Be forms.",
        micro_homework="Contrast I am and she is.",
        estimated_cefr="B1",
        errors=[
            LanguageError(
                rule_id="verb_be",
                original="I is ready",
                corrected="I am ready",
                explanation="Use am with I.",
                likely_cause="Possibly an unpractised form.",
                cause_evidence="One example; not enough evidence to establish a cause.",
                next_step="Say three personal sentences with I am.",
            )
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_analysis", [False, True])
async def test_five_turn_practice_feedback_history_and_vocabulary(
    tmp_path: Path,
    monkeypatch,
    fail_analysis: bool,
):
    db = Database(tmp_path / "practice.sqlite3")
    await db.init()
    await db.upsert_user(1, 10, "learner", "Learner")
    await db.complete_onboarding(
        1,
        {
            "english_level": "B1",
            "goal": "ielts",
            "interface_language": "en",
            "correction_style": "after_session",
        },
    )
    turns = 0

    async def generate(**kwargs):
        nonlocal turns
        schema = kwargs["schema"]
        if schema is TopicChoice:
            raise RuntimeError("Topic service unavailable")
        if schema is TutorReply:
            turns += 1
            if turns == 2:
                raise RuntimeError("Tutor temporarily unavailable")
            return TutorReply(reply="Thank you.", should_finish=True)
        if schema is Feedback:
            if fail_analysis:
                raise RuntimeError("Evaluation unavailable")
            return assessment()
        if schema is MemoryUpdate:
            return MemoryUpdate()
        if schema is VocabularyUpdate:
            return VocabularyUpdate(
                phrases=[
                    {
                        "phrase": "I am ready",
                        "translation": "Я готов",
                        "note": "I + am",
                    }
                ]
            )
        raise AssertionError(f"Unexpected schema: {schema}")

    gateway = SimpleNamespace(generate_json=AsyncMock(side_effect=generate))
    bot_data = {
        "db": db,
        "settings": SimpleNamespace(min_dialogue_turns=3, max_dialogue_turns=4),
        "topic_selector": TopicSelector(),
        "tutor": Tutor(gateway),
        "evaluator": Evaluator(gateway),
        "memory_updater": MemoryUpdater(gateway),
        "vocabulary_extractor": VocabularyExtractor(gateway),
    }
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data=bot_data), bot=AsyncMock(), user_data={}
    )
    message = SimpleNamespace(
        text=None,
        voice=None,
        reply_text=AsyncMock(return_value=SimpleNamespace(edit_text=AsyncMock())),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, username="learner", first_name="Learner"),
        effective_chat=SimpleNamespace(id=10),
        effective_message=message,
    )

    async def send_text(update, context, text, voice_text, reply_markup=None, voice=None):
        await update.effective_message.reply_text(text, reply_markup=reply_markup)

    monkeypatch.setattr(handlers, "send_text_and_voice", send_text)
    await handlers.ielts_practice(update, context)
    for turn in range(1, 6):
        message.text = "I is ready" if turn == 1 else "I enjoy my work because it is interesting."
        await handlers.handle_practice_message(update, context)
        active = await db.get_active_session(1)
        if turn < 5:
            assert active is not None
            assert active["turn_count"] == turn
        else:
            assert active is None
    completed = (await db.get_completed_sessions(1))[0]
    assert completed["turn_count"] == 5
    texts = [call.args[0] for call in message.reply_text.call_args_list]
    assert any("Part 2" in text and "1–2 minutes" in text for text in texts)
    assert any("Part 3" in text for text in texts)
    if fail_analysis:
        assert not completed["feedback"]["analysis_available"]
        assert await db.get_learning_profile(1) == []
        assert await db.get_vocabulary_items(1) == []
        assert any("analysis is temporarily unavailable" in text for text in texts)
        assert not any("I am ready" in text for text in texts)
    else:
        assert completed["feedback"]["errors"][0]["original"] == "I is ready"
        assert (await db.get_learning_profile(1))[0]["rule_id"] == "verb_be"
        assert (await db.get_vocabulary_items(1))[0]["phrase"] == "I am ready"
        assert any("British Council" in text for text in texts)
        error_cards = [
            call
            for call in message.reply_text.call_args_list
            if "Possible cause (hypothesis)" in call.args[0]
        ]
        assert len(error_cards) == 1
        assert (
            error_cards[0]
            .kwargs["reply_markup"]
            .inline_keyboard[0][0]
            .callback_data.startswith(f"errors:page:{completed['id']}:")
        )


@pytest.mark.asyncio
async def test_error_card_cannot_read_another_users_session(tmp_path: Path):
    db = Database(tmp_path / "cards.sqlite3")
    await db.init()
    await db.upsert_user(1, 10, None, "Learner")
    session_id = await db.create_session(
        1,
        {
            "topic_id": "work",
            "title": "Work",
            "opening_question": "What do you do?",
        },
    )
    await db.add_message(session_id, "user", "I is ready")
    result = assessment()
    await db.complete_session(session_id, result.summary, result.model_dump())
    query = SimpleNamespace(
        message=SimpleNamespace(), answer=AsyncMock(), edit_message_text=AsyncMock()
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(application=SimpleNamespace(bot_data={"db": db}))
    await handlers.handle_error_callback(
        update, context, {"telegram_id": 2}, f"errors:page:{session_id}:0"
    )
    query.edit_message_text.assert_not_awaited()
    await handlers.handle_error_callback(
        update, context, {"telegram_id": 1}, f"errors:page:{session_id}:999"
    )
    assert "I is ready" in query.edit_message_text.call_args.kwargs["text"]
