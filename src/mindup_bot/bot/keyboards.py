from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


START_PRACTICE_LABEL = "🚀 Начать практику"
PROFILE_LABEL = "📊 Мой профиль"
SETTINGS_LABEL = "⚙️ Настройки"
HELP_LABEL = "❓ Помощь"
FINISH_LABEL = "✅ Завершить"
MENU_LABEL = "🏠 Меню"


LEVEL_OPTIONS = [
    ("A2", "A2"),
    ("B1", "B1"),
    ("B1+", "B1+"),
    ("B2", "B2"),
    ("Не уверен", "not_sure"),
]

GOAL_OPTIONS = [
    ("💼 Работа", "work"),
    ("🌍 Путешествия", "travel"),
    ("🎓 Учеба", "study"),
    ("🎙 Собеседования", "interviews"),
    ("🗣 Уверенность в речи", "speaking_confidence"),
    ("🧠 Мышление и самовыражение", "thinking_self_expression"),
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

CORRECTION_OPTIONS = [
    ("🌱 Мягкие исправления", "soft"),
    ("🎯 Прямые исправления", "direct"),
    ("🧾 Только после сессии", "after_session"),
]

REMINDER_OPTIONS = [
    ("🌅 Утром", "morning"),
    ("☀️ Днем", "afternoon"),
    ("🌙 Вечером", "evening"),
    ("🔕 Без напоминаний", "none"),
]

LANGUAGE_OPTIONS = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
]


def main_menu(language: str | None = "ru") -> ReplyKeyboardMarkup:
    if language == "en":
        buttons = [
            ["🚀 Start practice", "📊 My profile"],
            ["⚙️ Settings", "❓ Help"],
        ]
    else:
        buttons = [
            [START_PRACTICE_LABEL, PROFILE_LABEL],
            [SETTINGS_LABEL, HELP_LABEL],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, input_field_placeholder="Выбери действие")


def option_keyboard(step: str, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"onb:{step}:{value}")] for label, value in options]
    )


def topics_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    selected_set = set(selected)
    for label, value in TOPIC_OPTIONS:
        prefix = "✅" if value in selected_set else "▫️"
        rows.append([InlineKeyboardButton(f"{prefix} {label}", callback_data=f"onb:topics:{value}")])
    rows.append([InlineKeyboardButton("Готово", callback_data="onb:topics_done:done")])
    return InlineKeyboardMarkup(rows)


def practice_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[FINISH_LABEL, MENU_LABEL]],
        resize_keyboard=True,
        input_field_placeholder="Отправь voice или напиши ответ",
    )
