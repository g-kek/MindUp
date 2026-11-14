from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindup_bot.ai.schemas import MemoryUpdate, VocabularyUpdate
from mindup_bot.bot import handlers
from mindup_bot.db import Database


def good_feedback():
    return handlers.fallback_feedback("en").model_copy(
        update={
            "analysis_available": True,
            "summary": "Recovered feedback.",
            "estimated_cefr": "B1",
        }
    )


async def setup(tmp_path):
    db = Database(tmp_path / "retry.sqlite3")
    await db.init()
    await db.upsert_user(1, 10, "learner", "Learner")
    session_id = await db.create_session(
        1, {"topic_id": "home", "title": "Home", "opening_question": "Describe your home."}
    )
    await db.add_message(session_id, "user", "I live in a small flat.")
    fallback = handlers.fallback_feedback("en")
    await db.complete_session(session_id, fallback.summary, fallback.model_dump())
    evaluator = SimpleNamespace(evaluate=AsyncMock(return_value=good_feedback()))
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "db": db,
                "evaluator": evaluator,
                "memory_updater": SimpleNamespace(update=AsyncMock(return_value=MemoryUpdate())),
                "vocabulary_extractor": SimpleNamespace(
                    extract=AsyncMock(return_value=VocabularyUpdate())
                ),
            }
        ),
        bot=AsyncMock(),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, username="learner", first_name="Learner"),
        effective_chat=SimpleNamespace(id=10),
        effective_message=SimpleNamespace(
            reply_text=AsyncMock(return_value=SimpleNamespace(edit_text=AsyncMock()))
        ),
    )
    return db, session_id, evaluator, context, update


@pytest.mark.asyncio
async def test_analysis_recovers_failed_report_and_redisplays_without_duplicate_evaluation(
    tmp_path,
):
    db, session_id, evaluator, context, update = await setup(tmp_path)
    original = await db.get_session(session_id)
    await handlers.session_analysis(update, context)
    recovered = await db.get_session(session_id)
    assert recovered["feedback"]["analysis_available"]
    assert recovered["completed_at"] == original["completed_at"]
    assert (await db.get_progress(1))["completed_count"] == 1
    await handlers.session_analysis(update, context)
    evaluator.evaluate.assert_awaited_once()
    assert any(
        "Recovered feedback" in call.args[0]
        for call in update.effective_message.reply_text.call_args_list
    )
    assert not await db.complete_session(
        session_id, "Replace", good_feedback().model_dump(), retry_failed=True
    )


@pytest.mark.asyncio
async def test_failed_retry_preserves_saved_session_and_offers_retry_button(tmp_path):
    db, session_id, evaluator, context, update = await setup(tmp_path)
    evaluator.evaluate.side_effect = RuntimeError("API unavailable")
    original = await db.get_session(session_id)
    await handlers.session_analysis(update, context)
    assert (await db.get_session(session_id))["feedback"] == original["feedback"]
    markup = update.effective_message.reply_text.call_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data == f"analysis:retry:{session_id}"


@pytest.mark.asyncio
async def test_retry_callback_cannot_access_another_users_report(tmp_path):
    _db, session_id, evaluator, context, update = await setup(tmp_path)
    update.callback_query = SimpleNamespace(answer=AsyncMock())
    await handlers.handle_analysis_retry(
        update, context, {"telegram_id": 2}, f"analysis:retry:{session_id}"
    )
    evaluator.evaluate.assert_not_awaited()
    update.effective_message.reply_text.assert_not_awaited()
