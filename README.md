# dialogum

Telegram-бот для ежедневной 10-15 минутной практики английского через голос,
диалог и персонализированную обратную связь.

## MVP

- `/start` с онбордингом на 6 вопросов.
- Профиль пользователя: уровень, цель, темы, стиль исправлений, напоминания, язык UI.
- Daily practice session на 3-5 ходов.
- Разделенные AI-роли:
  - `TopicSelector`
  - `Tutor`
  - `Evaluator`
  - `MemoryUpdater`
- Голос пользователя: Telegram voice -> Gemini audio transcription.
- Голос бота: text -> `edge-tts` MP3 -> Telegram `send_voice`.
- SQLite-память: профиль, текущая сессия, сообщения, memory summaries, последние темы.
- Меню: practice, profile, settings, help.
- Оплата и реферальная программа в MVP скрыты и не подключены.

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Заполни `.env`:

```bash
TELEGRAM_BOT_TOKEN=...
GEMINI_API_KEY=...
```

Запуск:

```bash
mindup-bot
```

или:

```bash
python -m mindup_bot.main
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Тесты

```bash
pytest
```

## Важное про ключи

Не коммить `.env`. В репозитории должен быть только `.env.example`.
