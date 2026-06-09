from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


START_PRACTICE_LABEL = "🚀 Начать практику"
PROFILE_LABEL = "📊 Мой профиль"
SETTINGS_LABEL = "⚙️ Настройки"
HELP_LABEL = "❓ Помощь"
FINISH_LABEL = "✅ Завершить"
MENU_LABEL = "🏠 Меню"
CUSTOM_TOPIC_LABEL = "✍️ Своя тема"
VOCABULARY_LABEL = "📚 Словарь"
VOCABULARY_REVIEW_LABEL = "🔁 Повторить"
SUPPORT_LABEL = "🛟 Поддержка"
FEEDBACK_LABEL = "💬 Feedback"

START_PRACTICE_LABEL_EN = "🚀 Start practice"
PROFILE_LABEL_EN = "📊 My profile"
SETTINGS_LABEL_EN = "⚙️ Settings"
HELP_LABEL_EN = "❓ Help"
FINISH_LABEL_EN = "✅ Finish"
MENU_LABEL_EN = "🏠 Menu"
CUSTOM_TOPIC_LABEL_EN = "✍️ Custom topic"
VOCABULARY_LABEL_EN = "📚 Vocabulary"
VOCABULARY_REVIEW_LABEL_EN = "🔁 Review"
SUPPORT_LABEL_EN = "🛟 Support"
FEEDBACK_LABEL_EN = "💬 Feedback"


LEVEL_OPTIONS = [
    ("A2", "A2"),
    ("B1", "B1"),
    ("B1+", "B1+"),
    ("B2", "B2"),
    ("Не уверен", "not_sure"),
]

LEVEL_OPTIONS_EN = [
    ("A2", "A2"),
    ("B1", "B1"),
    ("B1+", "B1+"),
    ("B2", "B2"),
    ("Not sure", "not_sure"),
]

GOAL_OPTIONS = [
    ("💼 Работа", "work"),
    ("🌍 Путешествия", "travel"),
    ("🎓 Учеба", "study"),
    ("🎙 Собеседования", "interviews"),
    ("🗣 Уверенность в речи", "speaking_confidence"),
    ("🧠 Мышление и самовыражение", "thinking_self_expression"),
]

GOAL_OPTIONS_EN = [
    ("💼 Work", "work"),
    ("🌍 Travel", "travel"),
    ("🎓 Study", "study"),
    ("🎙 Interviews", "interviews"),
    ("🗣 Speaking confidence", "speaking_confidence"),
    ("🧠 Thinking and self-expression", "thinking_self_expression"),
]

TOPIC_OPTIONS = [
    ("💼 Работа и карьера", "work_career"),
    ("🧠 Психология", "psychology"),
    ("💻 Технологии", "technology"),
    ("🎬 Культура и медиа", "culture_media"),
    ("🏙 Повседневная жизнь", "everyday_life"),
    ("📈 Бизнес", "business"),
    ("🌐 Общество", "society"),
    ("🎲 Умные случайные темы", "random_smart_topics"),
]

TOPIC_OPTIONS_EN = [
    ("💼 Work and career", "work_career"),
    ("🧠 Psychology", "psychology"),
    ("💻 Technology", "technology"),
    ("🎬 Culture and media", "culture_media"),
    ("🏙 Everyday life", "everyday_life"),
    ("📈 Business", "business"),
    ("🌐 Society", "society"),
    ("🎲 Random smart topics", "random_smart_topics"),
]

CORRECTION_OPTIONS = [
    ("🌱 Мягкие исправления", "soft"),
    ("🎯 Прямые исправления", "direct"),
    ("🧾 Только после сессии", "after_session"),
]

CORRECTION_OPTIONS_EN = [
    ("🌱 Soft corrections", "soft"),
    ("🎯 Direct corrections", "direct"),
    ("🧾 Only after the session", "after_session"),
]

REMINDER_OPTIONS = [
    ("🌅 Утром", "morning"),
    ("☀️ Днем", "afternoon"),
    ("🌙 Вечером", "evening"),
    ("🔕 Без напоминаний", "none"),
]

REMINDER_OPTIONS_EN = [
    ("🌅 Morning", "morning"),
    ("☀️ Afternoon", "afternoon"),
    ("🌙 Evening", "evening"),
    ("🔕 No reminders", "none"),
]

LANGUAGE_OPTIONS = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
]

VOICE_OPTIONS = [
    ("Jenny · US female", "en-US-JennyNeural"),
    ("Guy · US male", "en-US-GuyNeural"),
    ("Sonia · UK female", "en-GB-SoniaNeural"),
    ("Ryan · UK male", "en-GB-RyanNeural"),
]


def main_menu(language: str | None = "ru") -> ReplyKeyboardMarkup:
    if language == "en":
        buttons = [
            [START_PRACTICE_LABEL_EN, PROFILE_LABEL_EN],
            [CUSTOM_TOPIC_LABEL_EN, VOCABULARY_LABEL_EN],
            [VOCABULARY_REVIEW_LABEL_EN, SUPPORT_LABEL_EN],
            [SETTINGS_LABEL_EN, HELP_LABEL_EN],
            [FEEDBACK_LABEL_EN],
        ]
        placeholder = "Choose an action"
    else:
        buttons = [
            [START_PRACTICE_LABEL, PROFILE_LABEL],
            [CUSTOM_TOPIC_LABEL, VOCABULARY_LABEL],
            [VOCABULARY_REVIEW_LABEL, SUPPORT_LABEL],
            [SETTINGS_LABEL, HELP_LABEL],
            [FEEDBACK_LABEL],
        ]
        placeholder = "Выбери действие"
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, input_field_placeholder=placeholder)


def option_keyboard(step: str, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"onb:{step}:{value}")] for label, value in options]
    )


def settings_keyboard(language: str | None = "ru") -> InlineKeyboardMarkup:
    if language == "en":
        buttons = [
            [InlineKeyboardButton("🏆 Level", callback_data="settings:edit:english_level")],
            [InlineKeyboardButton("🎯 Goal", callback_data="settings:edit:goal")],
            [InlineKeyboardButton("📚 Topics", callback_data="settings:edit:topics")],
            [InlineKeyboardButton("🧾 Corrections", callback_data="settings:edit:correction_style")],
            [InlineKeyboardButton("🔔 Reminder", callback_data="settings:edit:reminder_time")],
            [InlineKeyboardButton("🔊 Bot voice", callback_data="settings:edit:tts_voice")],
            [InlineKeyboardButton("🌐 Interface language", callback_data="settings:edit:interface_language")],
            [InlineKeyboardButton("⬅️ Back to menu", callback_data="settings:close")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("🏆 Уровень", callback_data="settings:edit:english_level")],
            [InlineKeyboardButton("🎯 Цель", callback_data="settings:edit:goal")],
            [InlineKeyboardButton("📚 Темы", callback_data="settings:edit:topics")],
            [InlineKeyboardButton("🧾 Исправления", callback_data="settings:edit:correction_style")],
            [InlineKeyboardButton("🔔 Напоминание", callback_data="settings:edit:reminder_time")],
            [InlineKeyboardButton("🔊 Голос бота", callback_data="settings:edit:tts_voice")],
            [InlineKeyboardButton("🌐 Язык интерфейса", callback_data="settings:edit:interface_language")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="settings:close")],
        ]
    return InlineKeyboardMarkup(buttons)


def settings_option_keyboard(
    field: str,
    options: list[tuple[str, str]],
    language: str | None = "ru",
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"settings:set:{field}:{value}")]
        for label, value in options
    ]
    back_label = "⬅️ Back" if language == "en" else "⬅️ Назад"
    rows.append([InlineKeyboardButton(back_label, callback_data="settings:back")])
    return InlineKeyboardMarkup(rows)


def settings_options_for(field: str, language: str | None = "ru") -> list[tuple[str, str]]:
    if field == "english_level":
        return LEVEL_OPTIONS_EN if language == "en" else LEVEL_OPTIONS
    if field == "goal":
        return GOAL_OPTIONS_EN if language == "en" else GOAL_OPTIONS
    if field == "correction_style":
        return CORRECTION_OPTIONS_EN if language == "en" else CORRECTION_OPTIONS
    if field == "reminder_time":
        return REMINDER_OPTIONS_EN if language == "en" else REMINDER_OPTIONS
    if field == "interface_language":
        return LANGUAGE_OPTIONS
    if field == "tts_voice":
        return VOICE_OPTIONS
    raise ValueError(f"Unsupported settings field: {field}")


def topics_keyboard(
    selected: list[str],
    mode: str = "onb",
    language: str | None = "ru",
) -> InlineKeyboardMarkup:
    rows = []
    selected_set = set(selected)
    topic_options = TOPIC_OPTIONS_EN if language == "en" else TOPIC_OPTIONS
    for label, value in topic_options:
        prefix = "✅" if value in selected_set else "▫️"
        callback_prefix = "settings:topic" if mode == "settings" else "onb:topics"
        rows.append([InlineKeyboardButton(f"{prefix} {label}", callback_data=f"{callback_prefix}:{value}")])
    done_callback = "settings:topics_done:done" if mode == "settings" else "onb:topics_done:done"
    done_label = "Done" if language == "en" else "Готово"
    rows.append([InlineKeyboardButton(done_label, callback_data=done_callback)])
    if mode == "settings":
        back_label = "⬅️ Back" if language == "en" else "⬅️ Назад"
        rows.append([InlineKeyboardButton(back_label, callback_data="settings:back")])
    return InlineKeyboardMarkup(rows)


def practice_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[FINISH_LABEL, MENU_LABEL]],
        resize_keyboard=True,
        input_field_placeholder="Отправь voice или напиши ответ",
    )


def practice_reply_keyboard_for(language: str | None = "ru") -> ReplyKeyboardMarkup:
    if language == "en":
        return ReplyKeyboardMarkup(
            [[FINISH_LABEL_EN, MENU_LABEL_EN]],
            resize_keyboard=True,
            input_field_placeholder="Send a voice or type your answer",
        )
    return practice_reply_keyboard()


def practice_message_keyboard(message_id: int, language: str | None = "ru") -> InlineKeyboardMarkup:
    if language == "en":
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Translate", callback_data=f"practice:translate:{message_id}"),
                    InlineKeyboardButton("Topic words", callback_data=f"practice:topic_words:{message_id}"),
                ],
                [
                    InlineKeyboardButton("Finish", callback_data="practice:finish"),
                    InlineKeyboardButton("Menu", callback_data="practice:menu"),
                ],
            ]
        )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Перевести", callback_data=f"practice:translate:{message_id}"),
                InlineKeyboardButton("Слова по теме", callback_data=f"practice:topic_words:{message_id}"),
            ],
            [
                InlineKeyboardButton("Завершить", callback_data="practice:finish"),
                InlineKeyboardButton("Меню", callback_data="practice:menu"),
            ],
        ]
    )


def first_session_keyboard(language: str | None = "ru") -> InlineKeyboardMarkup:
    if language == "en":
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Start first practice", callback_data="welcome:practice")],
                [InlineKeyboardButton("Choose custom topic", callback_data="welcome:custom_topic")],
            ]
        )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Начать первую практику", callback_data="welcome:practice")],
            [InlineKeyboardButton("Выбрать свою тему", callback_data="welcome:custom_topic")],
        ]
    )


def skill_drill_keyboard(
    session_id: int,
    skill_slug: str,
    skill_label: str,
    language: str | None = "ru",
) -> InlineKeyboardMarkup:
    if language == "en":
        label = f"Train {skill_label}"
    else:
        label = f"Потренировать: {skill_label}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"drill:start:{session_id}:{skill_slug}")]]
    )
