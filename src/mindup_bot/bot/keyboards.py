from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


LEVEL_OPTIONS = [
    ("A2", "A2"),
    ("B1", "B1"),
    ("B1+", "B1+"),
    ("B2", "B2"),
    ("Not sure", "not_sure"),
]

GOAL_OPTIONS = [
    ("Work", "work"),
    ("Travel", "travel"),
    ("Study", "study"),
    ("Interviews", "interviews"),
    ("Speaking confidence", "speaking_confidence"),
    ("Thinking and self-expression", "thinking_self_expression"),
]

TOPIC_OPTIONS = [
    ("Work and career", "work_career"),
    ("Psychology", "psychology"),
    ("Technology", "technology"),
    ("Culture and media", "culture_media"),
    ("Everyday life", "everyday_life"),
    ("Business", "business"),
    ("Society", "society"),
    ("Random smart topics", "random_smart_topics"),
]

CORRECTION_OPTIONS = [
    ("Soft corrections", "soft"),
    ("Direct corrections", "direct"),
    ("Only after the session", "after_session"),
]

REMINDER_OPTIONS = [
    ("Morning", "morning"),
    ("Afternoon", "afternoon"),
    ("Evening", "evening"),
    ("No reminders", "none"),
]

LANGUAGE_OPTIONS = [
    ("Russian", "ru"),
    ("English", "en"),
]


def main_menu(language: str | None = "ru") -> InlineKeyboardMarkup:
    if language == "en":
        buttons = [
            [InlineKeyboardButton("Start today's practice", callback_data="menu:practice")],
            [InlineKeyboardButton("My progress", callback_data="menu:progress")],
            [InlineKeyboardButton("Settings", callback_data="menu:settings")],
            [InlineKeyboardButton("Subscription", callback_data="menu:subscription")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("Start today's practice", callback_data="menu:practice")],
            [InlineKeyboardButton("My progress", callback_data="menu:progress")],
            [InlineKeyboardButton("Settings", callback_data="menu:settings")],
            [InlineKeyboardButton("Subscription", callback_data="menu:subscription")],
        ]
    return InlineKeyboardMarkup(buttons)


def option_keyboard(step: str, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"onb:{step}:{value}")] for label, value in options]
    )


def topics_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    selected_set = set(selected)
    for label, value in TOPIC_OPTIONS:
        prefix = "[x]" if value in selected_set else "[ ]"
        rows.append([InlineKeyboardButton(f"{prefix} {label}", callback_data=f"onb:topics:{value}")])
    rows.append([InlineKeyboardButton("Done", callback_data="onb:topics_done:done")])
    return InlineKeyboardMarkup(rows)


def practice_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["/finish", "/menu"]],
        resize_keyboard=True,
        input_field_placeholder="Send a voice message or type in English",
    )

