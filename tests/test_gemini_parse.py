from mindup_bot.ai.gemini import parse_json_model
from mindup_bot.ai.schemas import TopicChoice


def test_parse_json_model_strips_markdown_fence() -> None:
    text = """
```json
{
  "topic_id": "work_focus",
  "title": "Work focus",
  "opening_question": "What helps you focus at work?",
  "rationale": "Matches the user goal."
}
```
"""

    topic = parse_json_model(text, TopicChoice)

    assert topic.topic_id == "work_focus"
    assert topic.opening_question == "What helps you focus at work?"

