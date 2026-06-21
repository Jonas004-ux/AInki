from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from card_state import deck_counts
import models

router = APIRouter(prefix="/decks", tags=["decks"])

# Anki-style hierarchy: deck names use "::" separators
# (e.g. "Production Management::5: Demand Forecasting").
SEP = "::"


class DeckCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class DeckRename(BaseModel):
    name: str


class DeckOut(BaseModel):
    id: int
    name: str
    description: str
    card_count: int = 0


def _ensure_parents(name: str, db: Session):
    """Auto-create intermediate parent decks so every level of an
    A::B::C path exists as a real deck (matches Anki)."""
    parts = name.split(SEP)
    for i in range(1, len(parts)):
        prefix = SEP.join(parts[:i])
        if not db.query(models.Deck).filter(models.Deck.name == prefix).first():
            db.add(models.Deck(name=prefix, description=""))
    db.flush()


@router.get("/", response_model=list[DeckOut])
def list_decks(db: Session = Depends(get_db)):
    decks = db.query(models.Deck).order_by(models.Deck.name).all()
    return [DeckOut(id=d.id, name=d.name, description=d.description, card_count=len(d.cards)) for d in decks]


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """Flat list of decks with direct new/learning/due counts. The frontend
    builds the tree from the '::' names and aggregates subtree counts."""
    now = datetime.utcnow()
    decks = db.query(models.Deck).order_by(models.Deck.name).all()
    out = []
    for d in decks:
        counts = deck_counts(d.cards, now)
        out.append({
            "id": d.id,
            "name": d.name,
            "new": counts["new"],
            "learning": counts["learning"],
            "due": counts["due"],
        })
    return out


@router.post("/", response_model=DeckOut)
def create_deck(payload: DeckCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Deck name required")
    if db.query(models.Deck).filter(models.Deck.name == name).first():
        raise HTTPException(status_code=400, detail="Deck name already exists")
    _ensure_parents(name, db)
    deck = models.Deck(name=name, description=payload.description)
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return DeckOut(id=deck.id, name=deck.name, description=deck.description, card_count=0)


@router.put("/{deck_id}/rename", response_model=DeckOut)
def rename_deck(deck_id: int, payload: DeckRename, db: Session = Depends(get_db)):
    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    old, new = deck.name, payload.name.strip()
    if not new:
        raise HTTPException(status_code=400, detail="Deck name required")
    # Rename this deck and re-prefix every descendant (A::* -> new::*).
    _ensure_parents(new, db)
    deck.name = new
    for child in db.query(models.Deck).filter(models.Deck.name.like(f"{old}{SEP}%")).all():
        child.name = new + child.name[len(old):]
    db.commit()
    db.refresh(deck)
    return DeckOut(id=deck.id, name=deck.name, description=deck.description, card_count=len(deck.cards))


@router.delete("/{deck_id}")
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    # Delete this deck and all its subdecks (cards cascade via the relationship).
    subdecks = db.query(models.Deck).filter(models.Deck.name.like(f"{deck.name}{SEP}%")).all()
    for sd in subdecks:
        db.delete(sd)
    db.delete(deck)
    db.commit()
    return {"ok": True, "deleted_subdecks": len(subdecks)}
