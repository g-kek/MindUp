from pydantic import BaseModel, Field


class TopicChoice(BaseModel):
    topic_id: str = Field(description="Stable snake_case topic identifier")
    title: str = Field(description="Short English title")
    opening_question: str = Field(description="One clear opening question in English")
    rationale: str = Field(description="Short reason why this topic fits the user")


class TutorReply(BaseModel):
    reply: str = Field(description="Brief natural coach response in English")
    follow_up: str | None = Field(default=None, description="Exactly one follow-up question if continuing")
    soft_correction: str | None = Field(default=None, description="At most one lightweight correction")
    should_finish: bool = Field(description="Whether the session should move to final feedback")

    def text_for_user(self) -> str:
        parts = [self.reply.strip()]
        if self.soft_correction:
            parts.append(f"Small upgrade: {self.soft_correction.strip()}")
        if self.follow_up:
            parts.append(self.follow_up.strip())
        return "\n\n".join(part for part in parts if part)


class ScoreItem(BaseModel):
    name: str
    score: int = Field(ge=1, le=5)
    note: str


class ImprovedPhrase(BaseModel):
    original: str
    improved: str


class Feedback(BaseModel):
    summary: str
    main_strength: str
    main_issue: str
    improved_phrases: list[ImprovedPhrase] = Field(min_length=2, max_length=2)
    micro_homework: str
    estimated_cefr: str
    scores: list[ScoreItem] = Field(min_length=4, max_length=5)


class MemoryItem(BaseModel):
    summary: str
    importance: int = Field(default=3, ge=1, le=5)


class MemoryUpdate(BaseModel):
    memories: list[MemoryItem] = Field(default_factory=list, max_length=5)


class TranslationResult(BaseModel):
    translation: str = Field(description="Natural translation of the source text")


class ProgressInsight(BaseModel):
    overall_summary: str = Field(description="Short cross-session progress summary")
    recent_change: str = Field(description="What changed across recent conversations")
    last_day_summary: str = Field(description="What happened during the last 24 hours")
    next_focus: str = Field(description="One practical next focus for the learner")
    achievements: list[str] = Field(default_factory=list, max_length=3)


class VocabularyPhrase(BaseModel):
    phrase: str = Field(description="Useful English phrase learned by the user")
    translation: str = Field(description="Translation in the user's interface language")
    note: str = Field(description="Short usage note in the user's interface language")


class VocabularyUpdate(BaseModel):
    phrases: list[VocabularyPhrase] = Field(default_factory=list, max_length=8)


class TopicVocabularyItem(BaseModel):
    phrase: str = Field(
        description="Useful English word, collocation, sentence starter, or typical conversation phrase"
    )
    translation: str = Field(description="Translation in the user's interface language")
    example: str = Field(description="Short English example sentence")


class TopicVocabulary(BaseModel):
    title: str = Field(description="Short title for the vocabulary list")
    items: list[TopicVocabularyItem] = Field(min_length=5, max_length=10)


class DrillTask(BaseModel):
    prompt: str = Field(description="Short test prompt in the user's interface language")
    answer: str = Field(description="Correct English answer or model answer")
    explanation: str = Field(description="Brief explanation in the user's interface language")


class SkillDrill(BaseModel):
    skill: str = Field(description="Target skill: vocabulary, grammar, clarity, communicative ability, etc.")
    title: str = Field(description="Short drill title in the user's interface language")
    tasks: list[DrillTask] = Field(min_length=5, max_length=10)
