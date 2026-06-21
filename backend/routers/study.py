"""
Endpoints for both Classic mode (SM-2 rating) and AI Answer Mode (evaluate + rate).
"""
import json
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
from sm2 import apply_sm2
from second_brain import (
    update_card_file,
    log_topic_answer,
    regenerate_topic_file,
    topic_accuracy,
    write_overview,
    card_tags,
)

router = APIRouter(prefix="/study", tags=["study"])


def _parse_verdict_json(text: str) -> dict:
    """Parse the evaluator's JSON, tolerating ```json fences or surrounding prose.
    Falls back to extracting the first {...} block. Coerces/validates fields so a
    malformed response never 500s the study flow."""
    raw = text.strip()
    # Strip a leading/trailing markdown code fence if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise HTTPException(status_code=502, detail="AI evaluator returned no JSON")
        data = json.loads(match.group(0))

    rating = int(data.get("rating", 0))
    rating = max(0, min(3, rating))
    verdict = data.get("verdict", "incorrect")
    if verdict not in ("correct", "partial", "incorrect"):
        verdict = "correct" if rating >= 2 else "incorrect"
    return {
        "verdict": verdict,
        "rating": rating,
        "feedback": str(data.get("feedback", "")).strip(),
        "ai_notes": str(data.get("ai_notes", "none")).strip(),
    }


class RateRequest(BaseModel):
    card_id: int
    rating: int  # 0=Again, 1=Hard, 2=Good, 3=Easy


class AIAnswerRequest(BaseModel):
    card_id: int
    user_answer: str


class AIAnswerResponse(BaseModel):
    verdict: str        # "correct" | "partial" | "incorrect"
    rating: int         # suggested SM-2 rating (0-3)
    feedback: str       # AI explanation
    ai_notes: str       # brief note saved to second brain


@router.post("/rate")
def rate_card(payload: RateRequest, db: Session = Depends(get_db)):
    """Classic mode: user self-rates after flipping the card."""
    card = db.query(models.Card).filter(models.Card.id == payload.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if payload.rating not in (0, 1, 2, 3):
        raise HTTPException(status_code=400, detail="Rating must be 0-3")
    apply_sm2(card, payload.rating)
    db.commit()
    return {"next_due": card.due_date, "interval": card.interval}


@router.post("/ai-answer", response_model=AIAnswerResponse)
def ai_answer(payload: AIAnswerRequest, db: Session = Depends(get_db)):
    """AI mode: evaluate user's free-text answer against the card back."""
    import anthropic

    card = db.query(models.Card).filter(models.Card.id == payload.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a strict but fair flashcard tutor. Evaluate the student's answer.

Card question: {card.front}
Correct answer: {card.back}
Student's answer: {payload.user_answer}

Respond in this exact JSON format (no markdown):
{{
  "verdict": "correct" | "partial" | "incorrect",
  "rating": 0-3,
  "feedback": "2-3 sentence explanation of what was right/wrong",
  "ai_notes": "one brief phrase about the gap (max 60 chars), or 'none' if fully correct"
}}

Rating guide: 3=Easy (perfect), 2=Good (correct with minor gaps), 1=Hard (partial, key points missing), 0=Again (wrong or too vague)."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    result = _parse_verdict_json(message.content[0].text)

    # Apply SM-2 and write to Second Brain
    apply_sm2(card, result["rating"])
    db.commit()

    # Hot path: rewrite the single card file + append one log line per topic.
    update_card_file(card, payload.user_answer, result["rating"], result["ai_notes"])
    for tag in card_tags(card):
        log_topic_answer(tag, card, result["rating"])

    return AIAnswerResponse(**result)


class EndSessionRequest(BaseModel):
    answered: int = 0
    correct: int = 0


@router.post("/end-session")
def end_session(payload: EndSessionRequest, db: Session = Depends(get_db)):
    """Batch the expensive writes: regenerate each touched topic's markdown
    summary and rebuild overview.md. Called once when a session ends, not
    per-answer."""
    # Gather every tag present across all cards, then regenerate its summary
    # from the append-only log + current card states.
    all_cards = db.query(models.Card).all()
    tag_to_cards: dict[str, list] = {}
    for c in all_cards:
        for tag in card_tags(c):
            tag_to_cards.setdefault(tag, []).append(c)

    topic_stats = []
    for tag, cards in tag_to_cards.items():
        total, acc = topic_accuracy(tag)
        if total == 0:
            continue  # never answered in AI mode — don't write a topic file
        regenerate_topic_file(tag, cards)
        topic_stats.append((tag, total, acc))

    # Weakest first (lowest accuracy)
    topic_stats.sort(key=lambda t: t[2])
    write_overview(
        topic_stats,
        {
            "answered": payload.answered,
            "correct": payload.correct,
            "needs_work": payload.answered - payload.correct,
        },
    )
    return {"topics_updated": len(topic_stats)}


@router.get("/today")
def today_stats(db: Session = Depends(get_db)):
    """Cards reviewed today (for the deck-overview footer line)."""
    from datetime import datetime, timedelta
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (
        db.query(models.Card)
        .filter(models.Card.last_reviewed >= start)
        .count()
    )
    return {"studied_today": count}
