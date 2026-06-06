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

