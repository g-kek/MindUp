from mindup_bot.bot.keyboards import settings_keyboard, settings_option_keyboard, topics_keyboard


def _button_texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_settings_keyboards_include_back_buttons() -> None:
    settings_texts = _button_texts(settings_keyboard("en"))
    option_texts = _button_texts(settings_option_keyboard("english_level", [("B1", "B1")], "en"))
    topics_texts = _button_texts(topics_keyboard(["technology"], mode="settings", language="en"))

    assert "⬅️ Back to menu" in settings_texts
    assert "⬅️ Back" in option_texts
    assert "⬅️ Back" in topics_texts

