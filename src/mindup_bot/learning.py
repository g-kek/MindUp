"""Evidence-backed learning history and a curated rule reference catalogue."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from mindup_bot.ai.schemas import Feedback

BC = "https://learnenglish.britishcouncil.org/free-resources/grammar/"
REFERENCE = BC + "english-grammar-reference/"
IELTS_SOURCE = (
    "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking"
)
# URLs come from this catalogue, never from model output. Broad reference pages are
# deliberately labelled as such rather than presented as a rule for a specific idiom.
RULES = {
    "tenses": ("Времена и вид", "Tenses and aspect", REFERENCE + "verbs"),
    "verb_be": (
        "Формы be и вспомогательные глаголы",
        "Be and auxiliaries",
        REFERENCE + "present-simple",
    ),
    "agreement": (
        "Согласование и окончания",
        "Agreement and endings",
        REFERENCE + "present-simple",
    ),
    "articles": ("Артикли", "Articles", BC + "a1-a2-grammar/articles-a-an-the"),
    "prepositions": ("Предлоги", "Prepositions", BC + "b1-b2/verbs-prepositions"),
    "verb_patterns": (
        "Глагольные шаблоны",
        "Verb patterns",
        BC + "a1-a2/verbs-followed-ing-or-infinitive",
    ),
    "word_order": (
        "Порядок слов и вопросы",
        "Word order and questions",
        REFERENCE + "clause-structure-verb-patterns",
    ),
    "conditionals": (
        "Условные предложения",
        "Conditionals",
        BC + "b1-b2/conditionals-zero-first-second",
    ),
    "modals": ("Модальные глаголы", "Modal verbs", REFERENCE + "modal-verbs"),
    "countability": (
        "Исчисляемость и множественное число",
        "Countability and plurals",
        REFERENCE + "nouns",
    ),
    "comparisons": ("Сравнения", "Comparisons", REFERENCE + "adjectives"),
    "relative_clauses": (
        "Относительные предложения",
        "Relative clauses",
        BC + "b1-b2/relative-clauses-defining-relative-clauses",
    ),
    "collocations": (
        "Сочетаемость слов",
        "Collocations",
        "https://dictionary.cambridge.org/grammar/british-grammar/collocation",
    ),
    "idioms": (
        "Устойчивые выражения",
        "Idioms",
        "https://dictionary.cambridge.org/grammar/british-grammar",
    ),
    "word_choice": (
        "Выбор слова и регистр",
        "Word choice and register",
        "https://dictionary.cambridge.org/grammar/british-grammar",
    ),
}
LEXICAL_RULES = {"collocations", "idioms", "word_choice"}


def rule_label(rule_id: str, language: str | None) -> str:
    rule = RULES[rule_id]
    return rule[1 if language == "en" else 0]


def grounded_feedback(feedback: Feedback, messages: list[dict[str, Any]]) -> Feedback:
    """Discard unsupported quotes before displaying or persisting AI observations.

    This verifies attribution, not grammatical correctness, which remains an AI judgement.
    Ambiguous transcriptions must not contribute to a longitudinal profile.
    """
    if not feedback.analysis_available:
        return feedback.model_copy(
            update={
                "errors": [],
                "correct_usage": [],
                "improved_phrases": [],
                "scores": [],
                "ielts": None,
            }
        )
    utterances = [str(m["content"]) for m in messages if m["role"] == "user"]

    def supported(quote: str) -> bool:
        return (
            bool(quote.strip())
            and "[unclear]" not in quote.lower()
            and any(quote in text and "[unclear]" not in text.lower() for text in utterances)
        )

    seen: set[tuple[str, str]] = set()
    errors = []
    for error in feedback.errors:
        key = (error.rule_id, error.original)
        if supported(error.original) and error.original != error.corrected and key not in seen:
            seen.add(key)
            errors.append(error)
    correct = []
    for usage in feedback.correct_usage:
        key = (usage.rule_id, usage.quote)
        conflict = any(
            error.rule_id == usage.rule_id
            and (error.original in usage.quote or usage.quote in error.original)
            for error in errors
        )
        if supported(usage.quote) and key not in seen and not conflict:
            seen.add(key)
            correct.append(usage)
    return feedback.model_copy(
        update={
            "errors": errors,
            "correct_usage": correct,
            "improved_phrases": [p for p in feedback.improved_phrases if supported(p.original)],
        }
    )


def learning_profile(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarise chronological observations; silence is never evidence of improvement.

    One session contributes one attempt per rule, with any error taking precedence.
    Separate session evidence avoids counting repeated words as repeated mastery.
    """
    grouped: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["rule_id"] in RULES:
            grouped[row["rule_id"]][row["session_id"]].append(row)
    result = []
    for rule_id, sessions in grouped.items():
        attempts = list(sessions.values())
        outcomes = [
            "error" if any(r["outcome"] == "error" for r in a) else "correct" for a in attempts
        ]
        error_sessions = outcomes.count("error")
        clean_streak = 0
        for outcome in reversed(outcomes):
            if outcome != "correct":
                break
            clean_streak += 1
        status = "observed"
        if error_sessions and clean_streak >= 3:
            status = "stabilizing"
        elif error_sessions and clean_streak >= 2:
            status = "improving"
        elif error_sessions >= 2:
            status = "recurring"
        elif error_sessions:
            status = "needs_practice"
        errors = [r for a in attempts for r in a if r["outcome"] == "error"]
        latest = errors[-1] if errors else attempts[-1][-1]
        result.append(
            {
                "rule_id": rule_id,
                "status": status,
                "error_sessions": error_sessions,
                "observed_sessions": len(outcomes),
                "recent_outcomes": outcomes[-8:],
                "clean_streak": clean_streak,
                "last_observed_at": attempts[-1][-1]["completed_at"],
                "last_error_at": errors[-1]["completed_at"] if errors else None,
                "example": latest["quote"],
                "details": latest.get("details", {}),
            }
        )
    priority = {
        "recurring": 0,
        "needs_practice": 1,
        "improving": 2,
        "stabilizing": 3,
        "observed": 4,
    }
    return sorted(
        result,
        key=lambda r: (
            priority[r["status"]],
            r["rule_id"] in LEXICAL_RULES,
            -r["error_sessions"],
            r["rule_id"],
        ),
    )


def priority_error_rule(feedback: Feedback, history: list[dict[str, Any]]) -> str | None:
    """Prioritise recurring grammar errors that actually appeared in this session."""
    current = {error.rule_id for error in feedback.errors}
    if not current:
        return None
    previous = {item["rule_id"]: item for item in history}
    return min(
        current,
        key=lambda rule: (
            rule in LEXICAL_RULES,
            -previous.get(rule, {}).get("error_sessions", 0),
            rule,
        ),
    )
