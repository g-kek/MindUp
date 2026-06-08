from mindup_bot.bot.keyboards import (
    main_menu,
    practice_message_keyboard,
    settings_keyboard,
    settings_option_keyboard,
    topics_keyboard,
)


def _button_texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_settings_keyboards_include_back_buttons() -> None:
    settings_texts = _button_texts(settings_keyboard("en"))
    option_texts = _button_texts(settings_option_keyboard("english_level", [("B1", "B1")], "en"))
    topics_texts = _button_texts(topics_keyboard(["technology"], mode="settings", language="en"))

    assert "⬅️ Back to menu" in settings_texts
    assert "🔊 Bot voice" in settings_texts
    assert "⬅️ Back" in option_texts
    assert "⬅️ Back" in topics_texts


def test_main_menu_and_practice_message_include_product_actions() -> None:
    menu_buttons = [button.text for row in main_menu("ru").keyboard for button in row]
    practice_texts = _button_texts(practice_message_keyboard(42, "ru"))

    assert "✍️ Своя тема" in menu_buttons
    assert "📚 Словарь" in menu_buttons
    assert "Перевести" in practice_texts
    assert "Завершить" in practice_texts
