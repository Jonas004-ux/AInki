"""
Shared logic for classifying a card into Anki's three overview buckets:
  - new (Neu):      never reviewed
  - learning (Nochmal): reviewed but lapsed (repetitions reset) and due now
  - due (Fällig):   graduated (repetitions >= 1) and due now

SQLite stores naive UTC datetimes, so we compare against a naive UTC "now".
"""
from datetime import datetime
from models import Card

NEW, LEARNING, DUE, NOT_DUE = "new", "learning", "due", "not_due"


def classify(card: Card, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    if card.last_reviewed is None:
        return NEW
    is_due = card.due_date is not None and card.due_date <= now
    if not is_due:
        return NOT_DUE
    return LEARNING if card.repetitions == 0 else DUE


def deck_counts(cards, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    counts = {"new": 0, "learning": 0, "due": 0}
    for c in cards:
        state = classify(c, now)
        if state in counts:
            counts[state] += 1
    return counts
