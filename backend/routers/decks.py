from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models

router = APIRouter(prefix="/decks", tags=["decks"])


class DeckCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class DeckOut(BaseModel):
    id: int
    name: str
    description: str
    card_count: int = 0

    class Config:
        from_attributes = True


@router.get("/", response_model=list[DeckOut])
def list_decks(db: Session = Depends(get_db)):
    decks = db.query(models.Deck).all()
    return [DeckOut(id=d.id, name=d.name, description=d.description, card_count=len(d.cards)) for d in decks]


@router.post("/", response_model=DeckOut)
def create_deck(payload: DeckCreate, db: Session = Depends(get_db)):
    if db.query(models.Deck).filter(models.Deck.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Deck name already exists")
    deck = models.Deck(name=payload.name, description=payload.description)
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return DeckOut(id=deck.id, name=deck.name, description=deck.description, card_count=0)


@router.delete("/{deck_id}")
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    db.delete(deck)
    db.commit()
    return {"ok": True}
