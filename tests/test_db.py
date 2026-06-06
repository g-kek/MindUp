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
    await db.add_message(session_id, "user", "It helps me work faster.")
    await db.increment_turn_count(session_id)

    active = await db.get_active_session(1)
    assert active is not None
    assert active["turn_count"] == 1

    messages = await db.get_session_messages(session_id)
    assert [message["role"] for message in messages] == ["tutor", "user"]

