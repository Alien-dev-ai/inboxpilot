"""Inspectable, deterministic baseline for candidate-message triage."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

INTENTS = (
    "interview_scheduling",
    "application_status",
    "offer_discussion",
    "withdrawal",
    "general_question",
    "document_request",
    "other",
)

@dataclass(frozen=True)
class Classification:
    intent: str
    priority: str
    reason: str
    matched_terms: tuple[str, ...]


RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("withdrawal", ("withdraw my application", "withdraw my candidacy", "no longer interested", "remove my application", "accept another offer")),
    ("offer_discussion", ("offer letter", "salary", "compensation", "negotiate", "offer details", "employment offer")),
    ("interview_scheduling", ("schedule an interview", "reschedule", "interview time", "available for an interview", "confirm the interview", "meeting invite")),
    ("document_request", ("submit my documents", "document", "resume", "résumé", "portfolio", "certificate", "work sample")),
    ("application_status", ("application status", "any update", "update on my application", "following up", "follow up", "heard back")),
    ("general_question", ("could you clarify", "i have a question", "more information", "please explain", "what does")),
    # "next steps" is a weak status signal; an explicit question phrase above takes precedence.
    ("application_status", ("next steps",)),
)

# Terms whose plain substring match caused false positives; all other terms match as substrings.
TERM_PATTERNS = {
    # Whole word, optionally plural: not "documentation" or "documented".
    "document": re.compile(r"\bdocuments?\b"),
    # The noun only, not the verb ("resume our conversation").
    "resume": re.compile(
        r"\b(?:my|the|a|an|your|updated|attached)\s+resume\b|\bresume\s+(?:is\s+)?attached\b"
        r"|\b(?:cv|cover letter|portfolio)\s+(?:and|or)\s+resume\b"
    ),
    # A salary range or salary expectations question does not imply an offer exists.
    "salary": re.compile(r"\bsalary\b(?![\s-]+(?:ranges?|expectations?)\b)"),
    "compensation": re.compile(r"compensation(?![\s-]+ranges?\b)"),
}

# Withdrawal phrases are ignored when negated ("I'm not going to withdraw my application").
NEGATION_SENSITIVE_TERMS = frozenset(dict(RULES)["withdrawal"])
NEGATOR = re.compile(r"\b(?:not|never|no|cannot)\b|n['’]t\b")
CLAUSE_BREAK = re.compile(r"[.,;:!?]|\b(?:but|and|so|however|though)\b")
NEGATION_WINDOW_WORDS = 5
# A comma-enclosed aside ("I do not, under any circumstances, want to ...") does not end the clause.
COMMA_ASIDE = re.compile(r",(?:(?!\b(?:but|and|so|however|though)\b)[^,.;:!?])*,")

def _is_negated(text: str, start: int) -> bool:
    """True if a negator appears in the few words before `start`, within the same clause."""
    clause = CLAUSE_BREAK.split(COMMA_ASIDE.sub(" ", text[:start]))[-1]
    return bool(NEGATOR.search(" ".join(clause.split()[-NEGATION_WINDOW_WORDS:])))

def _matches(term: str, text: str) -> bool:
    if term in NEGATION_SENSITIVE_TERMS:
        return any(not _is_negated(text, m.start()) for m in re.finditer(re.escape(term), text))
    pattern = TERM_PATTERNS.get(term)
    return bool(pattern.search(text)) if pattern else term in text

# A bare date or time reference ("today") is not urgency; only time-limit phrasing is.
HIGH_PRIORITY_TERMS = (
    "by today", "end of today", "urgent", "deadline", "within an hour", "in 1 hour",
    "offer expires", "need to reschedule", "cannot attend",
)

# "low" is only for clear courtesy-only messages; any request signal keeps them "normal".
COURTESY_TERMS = ("thank you for your time", "just wanted to say thank you", "thanks for your time")
REQUEST_SIGNAL = re.compile(r"\?|\bplease\b")

def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()

def classify_message(message: object, subject: object = "") -> Classification:
    """Classify text with simple keyword rules; ambiguous text defaults to review."""
    text = _normalise(f"{subject} {message}")
    if not text:
        return Classification("other", "normal", "Message is empty; human review required.", ())

    priority = "high" if any(term in text for term in HIGH_PRIORITY_TERMS) else "normal"
    urgency_note = " Time-sensitive wording detected; verify urgency manually." if priority == "high" else ""

    for intent, terms in RULES:
        matches = tuple(term for term in terms if _matches(term, text))
        if matches:
            reason = f"Matched {intent.replace('_', ' ')} phrase(s): {', '.join(matches[:3])}."
            return Classification(intent, priority, reason + urgency_note, matches)

    # Reached only with no matched intent; urgency ("high") always takes precedence.
    courtesy = tuple(term for term in COURTESY_TERMS if term in text)
    if priority == "normal" and courtesy and not REQUEST_SIGNAL.search(text):
        return Classification(
            "other",
            "low",
            f"Courtesy phrase(s) only: {', '.join(courtesy)}. No request detected; human review still required.",
            (),
        )

    return Classification(
        "other",
        priority,
        "No confident keyword match; human review required." + urgency_note,
        (),
    )

def classify_many(messages: Iterable[tuple[object, object]]) -> list[Classification]:
    """Classify an iterable of (message, subject) pairs."""
    return [classify_message(message, subject) for message, subject in messages]
