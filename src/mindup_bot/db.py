from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


@dataclass(frozen=True)
class Database:
    path: Path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connect() as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    interface_language TEXT,
                    english_level TEXT,
                    goal TEXT,
                    topics_json TEXT NOT NULL DEFAULT '[]',
                    correction_style TEXT,
                    reminder_time TEXT,
                    custom_topic_pending INTEGER NOT NULL DEFAULT 0,
                    pending_action TEXT,
                    review_item_id INTEGER,
                    tts_voice TEXT,
                    onboarding_completed INTEGER NOT NULL DEFAULT 0,
                    onboarding_step TEXT,
                    onboarding_data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic_id TEXT NOT NULL,
                    topic_title TEXT NOT NULL,
                    opening_question TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    summary TEXT,
                    feedback_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    voice_file_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    importance INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS used_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS vocabulary_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    phrase TEXT NOT NULL,
                    translation TEXT,
                    note TEXT,
                    source_session_id INTEGER,
                    times_seen INTEGER NOT NULL DEFAULT 1,
                    learned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id),
                    FOREIGN KEY(source_session_id) REFERENCES sessions(id),
                    UNIQUE(user_id, phrase)
                );

                CREATE TABLE IF NOT EXISTS progress_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    scope TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS contact_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    message TEXT NOT NULL,
                    forwarded_chat_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user_status
                    ON sessions(user_id, status, created_at);
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON session_messages(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_memories_user
                    ON memories(user_id, importance, created_at);
                CREATE INDEX IF NOT EXISTS idx_used_topics_user
                    ON used_topics(user_id, used_at);
                CREATE INDEX IF NOT EXISTS idx_vocabulary_user
                    ON vocabulary_items(user_id, last_seen_at);
                CREATE INDEX IF NOT EXISTS idx_progress_reports_user
                    ON progress_reports(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_contact_messages_user
                    ON contact_messages(user_id, created_at);
                """
            )
            await self._ensure_column(
                db,
                "users",
                "custom_topic_pending",
                "INTEGER NOT NULL DEFAULT 0",
            )
            await self._ensure_column(db, "users", "pending_action", "TEXT")
            await self._ensure_column(db, "users", "review_item_id", "INTEGER")
            await self._ensure_column(db, "users", "tts_voice", "TEXT")
            await db.commit()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = aiosqlite.Row
        try:
            yield connection
        finally:
            await connection.close()

    async def _fetchone(
        self,
        db: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> aiosqlite.Row | None:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def _fetchall(
        self,
        db: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[aiosqlite.Row]:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def _ensure_column(
        self,
        db: aiosqlite.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        rows = await self._fetchall(db, f"PRAGMA table_info({table})")
        if column in {row["name"] for row in rows}:
            return
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def upsert_user(
        self,
        telegram_id: int,
        chat_id: int,
        username: str | None,
        first_name: str | None,
    ) -> dict[str, Any]:
        async with self.connect() as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, chat_id, username, first_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    username = excluded.username,
                    first_name = excluded.first_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_id, chat_id, username, first_name),
            )
            await db.commit()
        user = await self.get_user(telegram_id)
        if user is None:
            raise RuntimeError("Failed to create user")
        return user

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            )
        if row is None:
            return None
        return self._user_from_row(row)

    async def set_onboarding_step(self, telegram_id: int, step: str) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE users
                SET onboarding_step = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                (step, telegram_id),
            )
            await db.commit()

    async def update_onboarding_data(self, telegram_id: int, data: dict[str, Any], step: str) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE users
                SET onboarding_data_json = ?, onboarding_step = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                (_json_dumps(data), step, telegram_id),
            )
            await db.commit()

    async def complete_onboarding(self, telegram_id: int, data: dict[str, Any]) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE users
                SET
                    interface_language = ?,
                    english_level = ?,
                    goal = ?,
                    topics_json = ?,
                    correction_style = ?,
                    reminder_time = ?,
                    onboarding_completed = 1,
                    onboarding_step = NULL,
                    onboarding_data_json = '{}',
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                (
                    data.get("interface_language"),
                    data.get("english_level"),
                    data.get("goal"),
                    _json_dumps(data.get("topics", [])),
                    data.get("correction_style"),
                    data.get("reminder_time"),
                    telegram_id,
                ),
            )
            await db.commit()

    async def update_user_settings(self, telegram_id: int, updates: dict[str, Any]) -> None:
        allowed_fields = {
            "interface_language",
            "english_level",
            "goal",
            "topics",
            "correction_style",
            "reminder_time",
            "custom_topic_pending",
            "pending_action",
            "review_item_id",
            "tts_voice",
        }
        unknown_fields = set(updates) - allowed_fields
        if unknown_fields:
            raise ValueError(f"Unsupported settings fields: {sorted(unknown_fields)}")
        if not updates:
            return

        assignments = []
        values = []
        for field, value in updates.items():
            if field == "topics":
                assignments.append("topics_json = ?")
                values.append(_json_dumps(value or []))
            else:
                assignments.append(f"{field} = ?")
                values.append(value)
        values.append(telegram_id)

        async with self.connect() as db:
            await db.execute(
                f"""
                UPDATE users
                SET {", ".join(assignments)},
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                tuple(values),
            )
            await db.commit()

    async def restart_onboarding(self, telegram_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE users
                SET onboarding_completed = 0,
                    onboarding_step = 'english_level',
                    onboarding_data_json = '{}',
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                (telegram_id,),
            )
            await db.commit()

    async def set_custom_topic_pending(self, telegram_id: int, is_pending: bool) -> None:
        await self.set_pending_action(telegram_id, "custom_topic" if is_pending else None)

    async def set_pending_action(
        self,
        telegram_id: int,
        action: str | None,
        review_item_id: int | None = None,
    ) -> None:
        await self.update_user_settings(
            telegram_id,
            {
                "custom_topic_pending": 1 if action == "custom_topic" else 0,
                "pending_action": action,
                "review_item_id": review_item_id,
            },
        )

    async def list_users_with_reminders(self) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT * FROM users
                WHERE onboarding_completed = 1
                    AND reminder_time IS NOT NULL
                    AND reminder_time != 'none'
                """
            )
        return [self._user_from_row(row) for row in rows]

    async def create_session(self, user_id: int, topic: dict[str, Any]) -> int:
        async with self.connect() as db:
            await db.execute(
                "UPDATE sessions SET status = 'abandoned' WHERE user_id = ? AND status = 'active'",
                (user_id,),
            )
            cursor = await db.execute(
                """
                INSERT INTO sessions (user_id, topic_id, topic_title, opening_question)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    topic["topic_id"],
                    topic["title"],
                    topic["opening_question"],
                ),
            )
            await db.execute(
                """
                INSERT INTO used_topics (user_id, topic_id, title)
                VALUES (?, ?, ?)
                """,
                (user_id, topic["topic_id"], topic["title"]),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_active_session(self, user_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                """
                SELECT * FROM sessions
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
        return dict(row) if row else None

    async def get_session(self, session_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            )
        return self._session_from_row(row) if row else None

    async def increment_turn_count(self, session_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE sessions
                SET turn_count = turn_count + 1
                WHERE id = ?
                """,
                (session_id,),
            )
            await db.commit()

    async def complete_session(self, session_id: int, summary: str, feedback: dict[str, Any]) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE sessions
                SET status = 'completed',
                    summary = ?,
                    feedback_json = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (summary, _json_dumps(feedback), session_id),
            )
            await db.commit()

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        voice_file_id: str | None = None,
    ) -> int:
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO session_messages (session_id, role, content, voice_file_id)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, voice_file_id),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_message_for_user(self, message_id: int, user_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                """
                SELECT session_messages.*
                FROM session_messages
                JOIN sessions ON sessions.id = session_messages.session_id
                WHERE session_messages.id = ? AND sessions.user_id = ?
                """,
                (message_id, user_id),
            )
        return dict(row) if row else None

    async def get_session_messages(self, session_id: int, limit: int = 20) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT * FROM (
                    SELECT * FROM session_messages
                    WHERE session_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                ORDER BY created_at ASC, id ASC
                """,
                (session_id, limit),
            )
        return [dict(row) for row in rows]

    async def get_recent_memories(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT * FROM memories
                WHERE user_id = ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        return [dict(row) for row in rows]

    async def add_memories(self, user_id: int, memories: list[dict[str, Any]]) -> None:
        if not memories:
            return
        async with self.connect() as db:
            await db.executemany(
                """
                INSERT INTO memories (user_id, summary, importance)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        user_id,
                        memory["summary"],
                        int(memory.get("importance", 3)),
                    )
                    for memory in memories
                    if memory.get("summary")
                ],
            )
            await db.commit()

    async def upsert_vocabulary_items(
        self,
        user_id: int,
        session_id: int,
        phrases: list[dict[str, Any]],
    ) -> None:
        clean_phrases = [
            phrase
            for phrase in phrases
            if str(phrase.get("phrase") or "").strip()
        ]
        if not clean_phrases:
            return
        async with self.connect() as db:
            await db.executemany(
                """
                INSERT INTO vocabulary_items (
                    user_id,
                    phrase,
                    translation,
                    note,
                    source_session_id
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, phrase) DO UPDATE SET
                    translation = excluded.translation,
                    note = excluded.note,
                    source_session_id = excluded.source_session_id,
                    times_seen = vocabulary_items.times_seen + 1,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        user_id,
                        str(phrase.get("phrase") or "").strip(),
                        str(phrase.get("translation") or "").strip(),
                        str(phrase.get("note") or "").strip(),
                        session_id,
                    )
                    for phrase in clean_phrases
                ],
            )
            await db.commit()

    async def get_vocabulary_items(self, user_id: int, limit: int = 30) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT *
                FROM vocabulary_items
                WHERE user_id = ?
                ORDER BY last_seen_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        return [dict(row) for row in rows]

    async def get_vocabulary_item(self, user_id: int, item_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                """
                SELECT *
                FROM vocabulary_items
                WHERE user_id = ? AND id = ?
                """,
                (user_id, item_id),
            )
        return dict(row) if row else None

    async def get_vocabulary_review_item(self, user_id: int) -> dict[str, Any] | None:
        async with self.connect() as db:
            row = await self._fetchone(
                db,
                """
                SELECT *
                FROM vocabulary_items
                WHERE user_id = ?
                ORDER BY last_seen_at ASC, id ASC
                LIMIT 1
                """,
                (user_id,),
            )
        return dict(row) if row else None

    async def mark_vocabulary_reviewed(self, user_id: int, item_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE vocabulary_items
                SET times_seen = times_seen + 1,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND id = ?
                """,
                (user_id, item_id),
            )
            await db.commit()

    async def get_recent_topics(self, user_id: int, limit: int = 8) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT topic_id, title, used_at FROM used_topics
                WHERE user_id = ?
                ORDER BY used_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        return [dict(row) for row in rows]

    async def get_progress(self, user_id: int) -> dict[str, Any]:
        async with self.connect() as db:
            count_row = await self._fetchone(
                db,
                """
                SELECT COUNT(*) AS completed_count
                FROM sessions
                WHERE user_id = ? AND status = 'completed'
                """,
                (user_id,),
            )
            last_row = await self._fetchone(
                db,
                """
                SELECT summary, feedback_json, completed_at
                FROM sessions
                WHERE user_id = ? AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            streak_rows = await self._fetchall(
                db,
                """
                SELECT DISTINCT substr(completed_at, 1, 10) AS completed_date
                FROM sessions
                WHERE user_id = ?
                    AND status = 'completed'
                    AND completed_at IS NOT NULL
                ORDER BY completed_date DESC
                LIMIT 60
                """,
                (user_id,),
            )
        last_feedback = _json_loads(last_row["feedback_json"], {}) if last_row else {}
        streak = _calculate_daily_streak(
            [
                row["completed_date"]
                for row in streak_rows
                if row["completed_date"]
            ]
        )
        return {
            "completed_count": int(count_row["completed_count"] if count_row else 0),
            "last_summary": last_row["summary"] if last_row else None,
            "last_completed_at": last_row["completed_at"] if last_row else None,
            "last_feedback": last_feedback,
            "streak": streak,
        }

    async def get_completed_sessions(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT *
                FROM sessions
                WHERE user_id = ? AND status = 'completed'
                ORDER BY completed_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
        return [self._session_from_row(row) for row in rows]

    async def get_completed_sessions_since(
        self,
        user_id: int,
        since: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        async with self.connect() as db:
            rows = await self._fetchall(
                db,
                """
                SELECT *
                FROM sessions
                WHERE user_id = ?
                    AND status = 'completed'
                    AND completed_at >= ?
                ORDER BY completed_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, since, limit),
            )
        return [self._session_from_row(row) for row in rows]

    async def add_progress_report(
        self,
        user_id: int,
        scope: str,
        report: dict[str, Any],
    ) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                INSERT INTO progress_reports (user_id, scope, report_json)
                VALUES (?, ?, ?)
                """,
                (user_id, scope, _json_dumps(report)),
            )
            await db.commit()

    async def add_contact_message(
        self,
        *,
        user: dict[str, Any],
        kind: str,
        message: str,
        forwarded_chat_id: str | None,
    ) -> int:
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO contact_messages (
                    user_id,
                    kind,
                    username,
                    first_name,
                    message,
                    forwarded_chat_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["telegram_id"],
                    kind,
                    user.get("username"),
                    user.get("first_name"),
                    message,
                    forwarded_chat_id,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    def _user_from_row(self, row: aiosqlite.Row) -> dict[str, Any]:
        user = dict(row)
        user["topics"] = _json_loads(user.pop("topics_json", "[]"), [])
        user["onboarding_data"] = _json_loads(user.pop("onboarding_data_json", "{}"), {})
        user["onboarding_completed"] = bool(user["onboarding_completed"])
        user["custom_topic_pending"] = bool(user.get("custom_topic_pending", 0))
        return user

    def _session_from_row(self, row: aiosqlite.Row) -> dict[str, Any]:
        session = dict(row)
        session["feedback"] = _json_loads(session.get("feedback_json"), {})
        return session


def _calculate_daily_streak(completed_dates: list[str]) -> dict[str, Any]:
    parsed_dates = sorted(
        {
            datetime.strptime(completed_date, "%Y-%m-%d").date()
            for completed_date in completed_dates
        },
        reverse=True,
    )
    today = datetime.now(timezone.utc).date()
    if not parsed_dates:
        return {
            "current": 0,
            "practiced_today": False,
            "last_practice_date": None,
        }

    practiced_today = parsed_dates[0] == today
    cursor = today if practiced_today else today - timedelta(days=1)
    current = 0
    date_set: set[date] = set(parsed_dates)
    while cursor in date_set:
        current += 1
        cursor -= timedelta(days=1)

    return {
        "current": current,
        "practiced_today": practiced_today,
        "last_practice_date": parsed_dates[0].isoformat(),
    }
