from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from card_state import classify
import models

router = APIRouter(prefix="/cards", tags=["cards"])

SEP = "::"


def _deck_and_subdeck_ids(deck_id: int, db: Session) -> list[int]:
    """A deck plus all its '::' descendants — studying a parent studies children."""
    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        return [deck_id]
    subs = db.query(models.Deck).filter(models.Deck.name.like(f"{deck.name}{SEP}%")).all()
    return [deck.id] + [s.id for s in subs]


class CardCreate(BaseModel):
    deck_id: int
    front: str
    back: str
    tags: Optional[str] = ""


class CardOut(BaseModel):
    id: int
    deck_id: int
    front: str
    back: str
    tags: str
    easiness: float
    interval: int
    repetitions: int
    due_date: Optional[datetime]
    last_reviewed: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/deck/{deck_id}", response_model=list[CardOut])
def list_cards(deck_id: int, db: Session = Depends(get_db)):
    return db.query(models.Card).filter(models.Card.deck_id == deck_id).all()


@router.get("/due/{deck_id}", response_model=list[CardOut])
def due_cards(deck_id: int, db: Session = Depends(get_db)):
    """Cards to study now for a deck and its subdecks: everything due
    (new cards are seeded due at creation time, so they're included)."""
    now = datetime.now(timezone.utc)
    deck_ids = _deck_and_subdeck_ids(deck_id, db)
    return (
        db.query(models.Card)
        .filter(models.Card.deck_id.in_(deck_ids), models.Card.due_date <= now)
        .all()
    )


class BrowseRow(BaseModel):
    id: int
    deck_id: int
    deck_name: str
    front: str
    back: str
    tags: str
    state: str  # new | learning | due | not_due
    due_date: Optional[datetime]


@router.get("/browse", response_model=list[BrowseRow])
def browse(
    q: str = "",
    deck_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Card Browser (Kartenverwaltung): every card with deck + state, with an
    optional text search over front/back/tags and an optional deck filter
    (includes that deck's subdecks)."""
    now = datetime.utcnow()
    query = db.query(models.Card, models.Deck.name).join(
        models.Deck, models.Card.deck_id == models.Deck.id
    )
    if deck_id is not None:
        query = query.filter(models.Card.deck_id.in_(_deck_and_subdeck_ids(deck_id, db)))
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            models.Card.front.ilike(like),
            models.Card.back.ilike(like),
            models.Card.tags.ilike(like),
        ))
    rows = query.order_by(models.Deck.name, models.Card.id).all()
    return [
        BrowseRow(
            id=c.id, deck_id=c.deck_id, deck_name=deck_name,
            front=c.front, back=c.back, tags=c.tags or "",
            state=classify(c, now), due_date=c.due_date,
        )
        for c, deck_name in rows
    ]


class MoveRequest(BaseModel):
    card_ids: list[int]
    target_deck_id: int


@router.post("/move")
def move_cards(payload: MoveRequest, db: Session = Depends(get_db)):
    """Bulk-move cards to another deck (Card Browser action)."""
    if not db.query(models.Deck).filter(models.Deck.id == payload.target_deck_id).first():
        raise HTTPException(status_code=404, detail="Target deck not found")
    updated = (
        db.query(models.Card)
        .filter(models.Card.id.in_(payload.card_ids))
        .update({models.Card.deck_id: payload.target_deck_id}, synchronize_session=False)
    )
    db.commit()
    return {"moved": updated}


@router.post("/", response_model=CardOut)
def create_card(payload: CardCreate, db: Session = Depends(get_db)):
    deck = db.query(models.Deck).filter(models.Deck.id == payload.deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    card = models.Card(
        deck_id=payload.deck_id,
        front=payload.front,
        back=payload.back,
        tags=payload.tags,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/{card_id}", response_model=CardOut)
def update_card(card_id: int, payload: CardCreate, db: Session = Depends(get_db)):
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.front = payload.front
    card.back = payload.back
    card.tags = payload.tags
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return {"ok": True}
