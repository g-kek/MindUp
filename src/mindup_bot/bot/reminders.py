from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes

from mindup_bot.db import Database

REMINDER_TIMES = {
    "morning": time(hour=9, minute=0),
    "afternoon": time(hour=14, minute=0),
    "evening": time(hour=19, minute=0),
}


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data["chat_id"]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Time for 10 minutes of English thinking practice.",
    )


def schedule_user_reminder(application: Application, user: dict, timezone_name: str) -> None:
    reminder = user.get("reminder_time")
    if reminder not in REMINDER_TIMES or application.job_queue is None:
        return

    job_name = f"daily-reminder:{user['telegram_id']}"
    for job in application.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    reminder_time = REMINDER_TIMES[reminder].replace(tzinfo=ZoneInfo(timezone_name))
    application.job_queue.run_daily(
        reminder_job,
        time=reminder_time,
        data={"chat_id": user["chat_id"]},
        name=job_name,
    )


async def schedule_existing_reminders(application: Application, db: Database, timezone_name: str) -> None:
    users = await db.list_users_with_reminders()
    for user in users:
        schedule_user_reminder(application, user, timezone_name)

