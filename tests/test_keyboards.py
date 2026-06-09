from mindup_bot.bot.keyboards import (
    first_session_keyboard,
    main_menu,
    practice_message_keyboard,
    settings_keyboard,
    settings_option_keyboard,
    skill_drill_keyboard,
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
    assert "🔁 Повторить" in menu_buttons
    assert "🛟 Поддержка" in menu_buttons
    assert "💬 Feedback" in menu_buttons
    assert "Перевести" in practice_texts
    assert "Слова по теме" in practice_texts
    assert "Завершить" in practice_texts


def test_first_session_keyboard_has_primary_paths() -> None:
    texts = _button_texts(first_session_keyboard("ru"))

    assert "Начать первую практику" in texts
    assert "Выбрать свою тему" in texts


def test_skill_drill_keyboard_points_to_session_and_skill() -> None:
    markup = skill_drill_keyboard(7, "vocabulary", "Vocabulary", "en")
    button = markup.inline_keyboard[0][0]

    assert button.text == "Train Vocabulary"
    assert button.callback_data == "drill:start:7:vocabulary"
