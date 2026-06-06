from __future__ import annotations

import json
from typing import Any

from mindup_bot.ai.gemini import GeminiGateway
from mindup_bot.ai.schemas import Feedback, MemoryUpdate, TopicChoice, TutorReply


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2)


class TopicSelector:
    system_instruction = """
You are TopicSelector for a daily English speaking practice bot.
Pick one fresh, discussable topic that fits the user's CEFR level, goals, interests, memories,
and recently used topics. The result must be practical for a 10-minute speaking session.
Avoid repeating recent topics. Ask exactly one opening question in English.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def select(
        self,
        *,
        profile: dict[str, Any],
        memories: list[dict[str, Any]],
        recent_topics: list[dict[str, Any]],
    ) -> TopicChoice:
        prompt = f"""
User profile:
{_compact_json(_profile_view(profile))}

Relevant memory summaries:
{_compact_json([m["summary"] for m in memories])}

Recently used topics:
{_compact_json([t["title"] for t in recent_topics])}

Choose a topic. Keep the opening question accessible for {profile.get("english_level") or "B1"}.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=TopicChoice,
            temperature=0.7,
        )


class Tutor:
    system_instruction = """
You are Tutor, an English Thinking Coach for A2-B2 learners.
Reply in English. Be concise, natural, and useful. Ask one follow-up question when continuing.
Push the user toward reasons, examples, comparisons, nuance, and clearer thinking.
Do not overcorrect. Give at most one small correction only when it helps immediately.
If the session should finish, do not ask a new question.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def respond(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        messages: list[dict[str, Any]],
        user_message: str,
        turn_number: int,
        min_turns: int,
        max_turns: int,
    ) -> TutorReply:
        correction_style = profile.get("correction_style") or "soft"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Current topic: {session["topic_title"]}
Opening question: {session["opening_question"]}
Correction preference: {correction_style}
Turn number after this user message: {turn_number}
Minimum turns before finishing: {min_turns}
Maximum turns: {max_turns}

Recent dialogue:
{_compact_json([{"role": m["role"], "content": m["content"]} for m in messages[-10:]])}

Latest user message:
{user_message}

Return a short coach response. Continue until at least {min_turns} user turns.
At turn {max_turns}, set should_finish=true and provide a short closing response.
""".strip()
        reply = await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=TutorReply,
            temperature=0.55,
        )
        if turn_number < min_turns:
            reply.should_finish = False
        if turn_number >= max_turns:
            reply.should_finish = True
            reply.follow_up = None
        return reply


class Evaluator:
    system_instruction = """
You are Evaluator for an English speaking practice session.
Give short, specific, supportive feedback. Focus on communicative ability, clarity, vocabulary,
grammar patterns, and argumentation. Do not be overly enthusiastic. Use English.
Return exactly: summary, one strength, one issue, two improved phrases, one micro-homework,
estimated CEFR, and 4-5 scores from 1 to 5.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def evaluate(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> Feedback:
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}

Dialogue:
{_compact_json([{"role": m["role"], "content": m["content"]} for m in messages])}

Evaluate the user's English only from this session. Keep each field concise.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=Feedback,
            temperature=0.35,
        )


class MemoryUpdater:
    system_instruction = """
You are MemoryUpdater. Extract durable, useful memory summaries for future English practice.
Keep only stable preferences, recurring mistakes, interests, goals, confidence issues,
and topics worth revisiting. Do not store sensitive personal details.
Return 0-5 compact memory items.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def update(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        messages: list[dict[str, Any]],
        feedback: Feedback,
    ) -> MemoryUpdate:
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}

Dialogue:
{_compact_json([{"role": m["role"], "content": m["content"]} for m in messages])}

Feedback:
{feedback.model_dump_json()}

Create memory summaries for future sessions.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=MemoryUpdate,
            temperature=0.25,
        )


def _profile_view(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "english_level": profile.get("english_level"),
        "goal": profile.get("goal"),
        "topics": profile.get("topics", []),
        "correction_style": profile.get("correction_style"),
        "reminder_time": profile.get("reminder_time"),
        "interface_language": profile.get("interface_language"),
    }

