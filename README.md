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
- Своя тема: пользователь может написать тему и начать сессию вокруг нее.
- Перевод tutor-текста по inline-кнопке под сообщением.
- Анализ прогресса по последним сессиям и последним 24 часам.
- Словарь изученных фраз с сохранением после разбора сессии.
- Повторение словаря через короткий translate-back quiz.
- Daily streak по завершенным практикам.
- Support и feedback формы с пересылкой в Telegram-группы.
- Разбор сессии выводится на языке интерфейса пользователя.
- Голос бота выбирается в настройках.
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

Если Gemini возвращает временный `503 UNAVAILABLE` из-за высокой нагрузки, бот пробует
fallback-модели из `.env`:

```bash
GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite
GEMINI_STT_FALLBACK_MODELS=gemini-2.5-flash-lite
```

Для support/feedback можно указать Telegram chat id групп:

```bash
SUPPORT_CHAT_ID=-100...
FEEDBACK_CHAT_ID=-100...
```

Если `FEEDBACK_CHAT_ID` не задан, feedback отправляется в `SUPPORT_CHAT_ID`.

Запуск:

```bash
mindup-bot
```

или:

```bash
python -m mindup_bot.main
```

Полезные команды:

```bash
/topic       # задать свою тему
/vocabulary  # открыть словарь фраз
/review      # повторить фразу из словаря
/progress    # профиль и анализ прогресса
/support     # написать в поддержку
/feedback    # отправить продуктовый feedback
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
