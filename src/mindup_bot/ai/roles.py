from __future__ import annotations

import json
from typing import Any

from mindup_bot.ai.gemini import GeminiGateway
from mindup_bot.ai.schemas import (
    Feedback,
    SkillDrill,
    MemoryUpdate,
    ProgressInsight,
    TopicChoice,
    TopicVocabulary,
    TranslationResult,
    TutorReply,
    VocabularyUpdate,
)


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

    async def from_custom_topic(
        self,
        *,
        profile: dict[str, Any],
        requested_topic: str,
    ) -> TopicChoice:
        prompt = f"""
User profile:
{_compact_json(_profile_view(profile))}

Requested topic:
{requested_topic}

Create one practical 10-minute speaking topic from the user's request.
Return an English title and exactly one accessible opening question in English.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=TopicChoice,
            temperature=0.55,
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
grammar patterns, and argumentation. Do not be overly enthusiastic.
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
        language: str,
    ) -> Feedback:
        feedback_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}

Dialogue:
{_compact_json([{"role": m["role"], "content": m["content"]} for m in messages])}

Evaluate the user's English only from this session. Keep each field concise.
Write summary, strength, issue, micro-homework, score names, and score notes in {feedback_language}.
Keep original and improved phrases in English.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=Feedback,
            temperature=0.35,
        )


class Translator:
    system_instruction = """
You translate short English learning-bot messages for a language learner.
Preserve meaning, keep formatting readable, and do not add commentary.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def translate(self, *, text: str, language: str) -> TranslationResult:
        target_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Target language: {target_language}

Text:
{text}
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=TranslationResult,
            temperature=0.2,
        )


class ProgressAnalyzer:
    system_instruction = """
You analyze progress for an English speaking practice learner.
Use recent completed sessions, feedback, and dialogue summaries.
Be concrete, avoid empty praise, and give one practical next focus.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def analyze(
        self,
        *,
        profile: dict[str, Any],
        recent_sessions: list[dict[str, Any]],
        last_day_sessions: list[dict[str, Any]],
        language: str,
    ) -> ProgressInsight:
        target_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Recent completed sessions:
{_compact_json([_session_view(session) for session in recent_sessions])}

Sessions from the last 24 hours:
{_compact_json([_session_view(session) for session in last_day_sessions])}

Write the whole report in {target_language}.
If there is not enough data, say that directly and still give a useful next focus.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=ProgressInsight,
            temperature=0.35,
        )


class VocabularyExtractor:
    system_instruction = """
You extract useful English phrases a learner studied during a speaking session.
Prefer corrected/improved phrases, reusable collocations, and concise sentence frames.
Return phrases worth saving to a personal vocabulary list.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def extract(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        messages: list[dict[str, Any]],
        feedback: Feedback,
        language: str,
    ) -> VocabularyUpdate:
        target_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}

Dialogue:
{_compact_json([{"role": m["role"], "content": m["content"]} for m in messages])}

Feedback:
{feedback.model_dump_json()}

For each phrase, write translation and note in {target_language}.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=VocabularyUpdate,
            temperature=0.25,
        )


class TopicVocabularyBuilder:
    system_instruction = """
You create compact topic vocabulary previews for English speaking practice.
Pick practical words, collocations, sentence starters, and typical conversational phrases
that help the learner discuss the topic out loud.
Avoid rare terms. Keep examples natural and useful for A2-B2 learners.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def build(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        language: str,
    ) -> TopicVocabulary:
        target_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}
Opening question: {session["opening_question"]}

Create 5-10 useful items for this topic.
Include both common words/collocations and typical conversational phrases or sentence frames.
Prefer items the learner can immediately say in a dialogue, for example "In my experience...",
"One reason is that...", "Could you explain what you mean by...".
Write translations in {target_language}. Keep examples in English.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=TopicVocabulary,
            temperature=0.35,
        )


class SkillDrillBuilder:
    system_instruction = """
You create short targeted English practice drills after a speaking session.
Focus on the learner's weakest feedback category and the session topic.
Each task must be test-like, practical, and answerable without extra context.
""".strip()

    def __init__(self, gemini: GeminiGateway) -> None:
        self._gemini = gemini

    async def build(
        self,
        *,
        profile: dict[str, Any],
        session: dict[str, Any],
        feedback: Feedback,
        skill: str,
        language: str,
    ) -> SkillDrill:
        target_language = "Russian" if language == "ru" else "English"
        prompt = f"""
Profile:
{_compact_json(_profile_view(profile))}

Topic: {session["topic_title"]}
Opening question: {session["opening_question"]}

Feedback:
{feedback.model_dump_json()}

Weakest skill to train: {skill}

Create 5-10 short test tasks for this skill and this topic.
For vocabulary: translate-back, choose a better word, or complete a phrase.
For grammar patterns: transform sentences or fill a missing structure.
For clarity/communicative ability: rewrite vague answers into clearer English.
Write prompts and explanations in {target_language}. Keep answers in English.
""".strip()
        return await self._gemini.generate_json(
            system_instruction=self.system_instruction,
            prompt=prompt,
            schema=SkillDrill,
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


def _session_view(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "topic_title": session.get("topic_title"),
        "turn_count": session.get("turn_count"),
        "summary": session.get("summary"),
        "completed_at": session.get("completed_at"),
        "feedback": session.get("feedback", {}),
    }
