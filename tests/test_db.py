from pathlib import Path

import pytest

from mindup_bot.db import Database


@pytest.mark.asyncio
async def test_user_onboarding_and_session_flow(tmp_path: Path) -> None:
    db = Database(tmp_path / "mindup.sqlite3")
    await db.init()

    user = await db.upsert_user(telegram_id=1, chat_id=10, username="u", first_name="User")
    assert user["onboarding_completed"] is False

    data = {
        "english_level": "B1",
        "goal": "work",
        "topics": ["technology", "business"],
        "correction_style": "soft",
        "reminder_time": "morning",
        "interface_language": "ru",
    }
    await db.complete_onboarding(1, data)
    user = await db.get_user(1)
    assert user is not None
    assert user["onboarding_completed"] is True
    assert user["topics"] == ["technology", "business"]

    session_id = await db.create_session(
        1,
        {
            "topic_id": "tech_at_work",
            "title": "Technology at work",
            "opening_question": "How does technology change your work?",
        },
    )
    await db.add_message(session_id, "tutor", "How does technology change your work?")
    message_id = await db.add_message(session_id, "user", "It helps me work faster.")
    await db.increment_turn_count(session_id)

    active = await db.get_active_session(1)
    assert active is not None
    assert active["turn_count"] == 1

    messages = await db.get_session_messages(session_id)
    assert [message["role"] for message in messages] == ["tutor", "user"]

    user_message = await db.get_message_for_user(message_id, 1)
    assert user_message is not None
    assert user_message["content"] == "It helps me work faster."


@pytest.mark.asyncio
async def test_update_user_settings_does_not_restart_onboarding(tmp_path: Path) -> None:
    db = Database(tmp_path / "mindup.sqlite3")
    await db.init()
    await db.upsert_user(telegram_id=1, chat_id=10, username="u", first_name="User")
    await db.complete_onboarding(
        1,
        {
            "english_level": "B1",
            "goal": "work",
            "topics": ["technology"],
            "correction_style": "soft",
            "reminder_time": "morning",
            "interface_language": "ru",
        },
    )

    await db.update_user_settings(
        1,
        {
            "interface_language": "en",
            "topics": ["technology", "business"],
            "reminder_time": "none",
            "tts_voice": "en-US-GuyNeural",
        },
    )
    await db.set_custom_topic_pending(1, True)

    user = await db.get_user(1)

    assert user is not None
    assert user["interface_language"] == "en"
    assert user["topics"] == ["technology", "business"]
    assert user["reminder_time"] == "none"
    assert user["tts_voice"] == "en-US-GuyNeural"
    assert user["custom_topic_pending"] is True
    assert user["pending_action"] == "custom_topic"
    assert user["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_vocabulary_and_completed_session_progress(tmp_path: Path) -> None:
    db = Database(tmp_path / "mindup.sqlite3")
    await db.init()
    await db.upsert_user(telegram_id=1, chat_id=10, username="u", first_name="User")
    session_id = await db.create_session(
        1,
        {
            "topic_id": "custom_work",
            "title": "Work",
            "opening_question": "What helps you focus at work?",
        },
    )
    feedback = {
        "summary": "The user practiced work vocabulary.",
        "estimated_cefr": "B1",
    }
    await db.complete_session(session_id, feedback["summary"], feedback)

    await db.upsert_vocabulary_items(
        1,
        session_id,
        [{"phrase": "I tend to agree", "translation": "я скорее согласен", "note": "Soft opinion"}],
    )
    await db.upsert_vocabulary_items(
        1,
        session_id,
        [{"phrase": "I tend to agree", "translation": "я скорее согласен", "note": "Soft opinion"}],
    )

    sessions = await db.get_completed_sessions(1)
    vocabulary = await db.get_vocabulary_items(1)
    review_item = await db.get_vocabulary_review_item(1)
    assert review_item is not None
    await db.set_pending_action(1, "vocab_review", review_item["id"])
    await db.mark_vocabulary_reviewed(1, review_item["id"])
    reviewed = await db.get_vocabulary_item(1, review_item["id"])

    assert sessions[0]["feedback"]["estimated_cefr"] == "B1"
    assert sessions[0]["summary"] == "The user practiced work vocabulary."
    assert sessions[0]["status"] == "completed"
    assert vocabulary[0]["phrase"] == "I tend to agree"
    assert vocabulary[0]["times_seen"] == 2
    assert reviewed is not None
    assert reviewed["times_seen"] == 3

    user = await db.get_user(1)
    assert user is not None
    assert user["pending_action"] == "vocab_review"
    assert user["review_item_id"] == review_item["id"]

    progress = await db.get_progress(1)
    assert progress["streak"]["current"] == 1
    assert progress["streak"]["practiced_today"] is True


@pytest.mark.asyncio
async def test_contact_messages_are_saved(tmp_path: Path) -> None:
    db = Database(tmp_path / "mindup.sqlite3")
    await db.init()
    user = await db.upsert_user(telegram_id=1, chat_id=10, username="user_name", first_name="User")

    message_id = await db.add_contact_message(
        user=user,
        kind="support",
        message="I need help",
        forwarded_chat_id="-100123",
    )

    assert message_id > 0
