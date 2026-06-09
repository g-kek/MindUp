from mindup_bot.bot.keyboards import (
    first_session_keyboard,
    main_menu,
    practice_message_keyboard,
    resume_practice_keyboard,
    settings_keyboard,
    settings_option_keyboard,
    short_session_finish_keyboard,
    skill_drill_pager_keyboard,
    skill_drill_keyboard,
    topic_vocabulary_pager_keyboard,
    topics_keyboard,
    vocabulary_pager_keyboard,
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
    assert "💬 Отзыв" in menu_buttons
    assert "Перевести" in practice_texts
    assert "Слова и фразы" in practice_texts
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


def test_vocabulary_pagers_have_left_right_controls() -> None:
    markup = vocabulary_pager_keyboard(1, 3, "ru")
    buttons = markup.inline_keyboard[0]

    assert buttons[0].text == "←"
    assert buttons[0].callback_data == "vocab:page:0"
    assert buttons[1].text == "2/3"
    assert buttons[2].callback_data == "vocab:page:2"


def test_topic_vocabulary_and_resume_keyboards() -> None:
    pager = topic_vocabulary_pager_keyboard(42, 0, 2, "ru")
    resume = resume_practice_keyboard("ru")

    assert pager.inline_keyboard[0][2].callback_data == "topic_vocab:page:42:1"
    assert resume.inline_keyboard[0][0].text == "Вернуться к практике"


def test_short_session_and_skill_drill_pager_keyboards() -> None:
    short_session = short_session_finish_keyboard("ru")
    drill_pager = skill_drill_pager_keyboard(7, "vocabulary", 0, 5, "ru")

    assert short_session.inline_keyboard[0][0].text == "Продолжить разговор"
    assert short_session.inline_keyboard[1][0].callback_data == "practice:force_finish"
    assert drill_pager.inline_keyboard[0][2].callback_data == "drill:page:7:vocabulary:1"
