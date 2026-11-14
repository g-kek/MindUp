from typing import Literal

from pydantic import BaseModel, Field, model_validator

RuleId = Literal[
    "tenses",
    "verb_be",
    "agreement",
    "articles",
    "prepositions",
    "verb_patterns",
    "word_order",
    "conditionals",
    "modals",
    "countability",
    "comparisons",
    "relative_clauses",
    "collocations",
    "idioms",
    "word_choice",
]


class TopicChoice(BaseModel):
    topic_id: str = Field(description="Stable snake_case topic identifier")
    title: str = Field(max_length=100, description="Short English title")
    opening_question: str = Field(
        max_length=500, description="One clear opening question in English"
    )
    rationale: str = Field(max_length=350, description="Short reason why this topic fits the user")
    practice_mode: Literal["ielts", "conversation"] = "ielts"
    second_question: str = Field(default="", max_length=400)
    cue_card: str = Field(default="", max_length=900)
    discussion_questions: list[str] = Field(default_factory=list, max_length=2)
    source_url: str = Field(default="", max_length=350)
    source_label: str = Field(default="", max_length=120)


class TutorReply(BaseModel):
    reply: str = Field(max_length=600, description="Brief natural coach response in English")
    follow_up: str | None = Field(
        default=None, max_length=1200, description="Exactly one follow-up question if continuing"
    )
    soft_correction: str | None = Field(
        default=None, max_length=350, description="At most one lightweight correction"
    )
    should_finish: bool = Field(description="Whether the session should move to final feedback")

    def text_for_user(self) -> str:
        parts = [self.reply.strip()]
        if self.soft_correction:
            parts.append(f"Small upgrade: {self.soft_correction.strip()}")
        if self.follow_up:
            parts.append(self.follow_up.strip())
        return "\n\n".join(part for part in parts if part)


class ScoreItem(BaseModel):
    name: str = Field(max_length=60)
    score: int = Field(ge=1, le=5)
    note: str = Field(max_length=180)


class ImprovedPhrase(BaseModel):
    original: str = Field(max_length=240)
    improved: str = Field(max_length=300)


class LanguageError(BaseModel):
    rule_id: RuleId
    original: str = Field(min_length=1, max_length=240, description="Exact learner quote")
    corrected: str = Field(min_length=1, max_length=300)
    explanation: str = Field(max_length=400)
    likely_cause: str = Field(max_length=300, description="Tentative hypothesis, never a diagnosis")
    cause_evidence: str = Field(
        max_length=240, description="Evidence or explicit insufficient data"
    )
    next_step: str = Field(max_length=300, description="Personalized concrete repair exercise")


class CorrectUsage(BaseModel):
    rule_id: RuleId
    quote: str = Field(min_length=1, max_length=240, description="Exact correct learner usage")


class IELTSAssessment(BaseModel):
    coherence: str = Field(max_length=350, description="Text evidence; no speech-rate claims")
    lexical_resource: str = Field(max_length=350)
    grammatical_range_accuracy: str = Field(max_length=350)
    # No pronunciation or overall band: the evaluator receives text, not audio.


class Feedback(BaseModel):
    summary: str = Field(max_length=400)
    main_strength: str = Field(max_length=300)
    main_issue: str = Field(max_length=300)
    improved_phrases: list[ImprovedPhrase] = Field(default_factory=list, max_length=2)
    micro_homework: str = Field(max_length=300)
    estimated_cefr: str = Field(
        max_length=40,
        description="One CEFR code only, e.g. B1 or A2+; no explanations",
    )
    scores: list[ScoreItem] = Field(default_factory=list, max_length=5)
    analysis_available: bool = True
    errors: list[LanguageError] = Field(default_factory=list, max_length=12)
    correct_usage: list[CorrectUsage] = Field(default_factory=list, max_length=15)
    ielts: IELTSAssessment | None = None


class MemoryItem(BaseModel):
    summary: str
    importance: int = Field(default=3, ge=1, le=5)


class MemoryUpdate(BaseModel):
    memories: list[MemoryItem] = Field(default_factory=list, max_length=5)


class TranslationResult(BaseModel):
    translation: str = Field(description="Natural translation of the source text")


class ProgressInsight(BaseModel):
    overall_summary: str = Field(max_length=500, description="Short cross-session progress summary")
    recent_change: str = Field(
        max_length=500, description="What changed across recent conversations"
    )
    last_day_summary: str = Field(
        max_length=500, description="What happened during the last 24 hours"
    )
    next_focus: str = Field(max_length=500, description="One practical next focus for the learner")
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
    skill: str = Field(
        description="Target skill: vocabulary, grammar, clarity, communicative ability, etc."
    )
    title: str = Field(description="Short drill title in the user's interface language")
    tasks: list[DrillTask] = Field(min_length=5, max_length=10)


class ContrastExample(BaseModel):
    sentence: str = Field(min_length=1, max_length=250)
    explanation: str = Field(min_length=1, max_length=300)


class RuleTask(BaseModel):
    kind: Literal["choose", "gap", "repair", "speaking"]
    prompt: str = Field(min_length=1, max_length=650)
    choices: list[str] = Field(default_factory=list, max_length=2)
    correct_choice: int | None = Field(default=None, ge=0, le=1)
    answer: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_choices(self) -> "RuleTask":
        if self.kind == "choose":
            if len(self.choices) != 2 or self.correct_choice is None:
                raise ValueError("Choice tasks require two options and a correct index")
            if any(not option.strip() or len(option) > 300 for option in self.choices):
                raise ValueError("Choice options must be nonempty and at most 300 characters")
            if self.choices[0].strip().casefold() == self.choices[1].strip().casefold():
                raise ValueError("Choice options must differ")
            if self.answer != self.choices[self.correct_choice]:
                raise ValueError("The answer must match the correct choice")
        elif self.choices or self.correct_choice is not None:
            raise ValueError("Only choice tasks can define choices")
        return self


class RuleLesson(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    overview: str = Field(min_length=1, max_length=600)
    focus_rules: list[RuleId] = Field(min_length=1, max_length=3)
    examples: list[ContrastExample] = Field(min_length=2, max_length=4)
    tasks: list[RuleTask] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_mix(self) -> "RuleLesson":
        kinds = [task.kind for task in self.tasks]
        if kinds.count("choose") != 2 or not {"gap", "repair", "speaking"}.issubset(kinds):
            raise ValueError("A lesson needs two choices, a gap, a repair and a speaking task")
        return self


class RuleAnswerEvaluation(BaseModel):
    outcome: Literal["correct", "partial", "incorrect"]
    feedback: str = Field(min_length=1, max_length=600)
    suggested_answer: str = Field(min_length=1, max_length=500)
    next_hint: str = Field(min_length=1, max_length=350)
