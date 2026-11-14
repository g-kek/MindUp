from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindup_bot.ai.roles import TopicSelector
from mindup_bot.bot.handlers import start_custom_topic_session
from mindup_bot.db import Database
from mindup_bot.exam_topics import (
    TOPICS,
    UnknownIELTSTopic,
    choose_exam_topic,
    requested_exam_topic,
)


@pytest.mark.asyncio
async def test_exam_selection_ignores_personal_preferences_and_memories():
    selector = TopicSelector()
    first = await selector.select(
        profile={"topics": ["technology"], "goal": "work"},
        memories=[{"summary": "Only practise software engineering."}],
        recent_topics=[],
    )
    other = await selector.select(
        profile={"topics": ["psychology"], "goal": "travel"},
        memories=[],
        recent_topics=[],
    )
    assert first == other
    assert first.topic_id in {f"ielts_{topic.slug}" for topic in TOPICS}
    assert first.source_url and first.source_label


def test_bank_covers_every_topic_before_repeating_and_has_full_plans():
    recent = []
    for _ in TOPICS:
        topic = choose_exam_topic(recent)
        assert topic.topic_id not in {item["topic_id"] for item in recent}
        assert topic.cue_card and len(topic.discussion_questions) == 2
        assert topic.source_url.startswith(
            ("https://takeielts.britishcouncil.org/", "https://ielts.idp.com/")
        )
        recent.insert(0, {"topic_id": topic.topic_id, "title": topic.title})
    assert choose_exam_topic(recent).topic_id == recent[-1]["topic_id"]


def test_manual_topics_are_bank_topics_and_arbitrary_topics_are_rejected():
    assert requested_exam_topic("путешествия").topic_id == "ielts_travel"
    assert requested_exam_topic("2").topic_id == "ielts_work_study"
    with pytest.raises(UnknownIELTSTopic):
        requested_exam_topic("quantum software architecture")
    with pytest.raises(UnknownIELTSTopic):
        requested_exam_topic("homework")  # Do not accidentally match the word 'work'.


@pytest.mark.asyncio
async def test_unknown_manual_topic_keeps_selection_pending_without_creating_session(tmp_path):
    db = Database(tmp_path / "topics.sqlite3")
    await db.init()
    user = await db.upsert_user(1, 1, None, "Learner")
    await db.set_custom_topic_pending(1, True)
    update = SimpleNamespace(
        effective_message=SimpleNamespace(reply_text=AsyncMock()),
        effective_chat=SimpleNamespace(id=1),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"db": db, "topic_selector": TopicSelector()}),
        bot=AsyncMock(),
    )
    await start_custom_topic_session(update, context, user, "quantum software architecture")
    assert await db.get_active_session(1) is None
    assert (await db.get_user(1))["pending_action"] == "custom_topic"
    assert "/train" in update.effective_message.reply_text.call_args.args[0]


def test_repeated_cycles_use_most_recent_occurrence_in_bounded_history():
    recent = []
    for _ in range(3):
        cycle = []
        for _topic in TOPICS:
            topic = choose_exam_topic(recent)
            cycle.append(topic.topic_id)
            recent.insert(0, {"topic_id": topic.topic_id, "title": topic.title})
            recent = recent[:32]
        assert len(set(cycle)) == len(TOPICS)
