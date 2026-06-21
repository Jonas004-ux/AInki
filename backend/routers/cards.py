from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
import models

router = APIRouter(prefix="/cards", tags=["cards"])


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
    now = datetime.now(timezone.utc)
    return (
        db.query(models.Card)
        .filter(models.Card.deck_id == deck_id, models.Card.due_date <= now)
        .all()
    )


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
