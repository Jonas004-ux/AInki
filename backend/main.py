import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
import models
from routers import decks, cards, study, config_router, chat

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AInki", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decks.router)
app.include_router(cards.router)
app.include_router(study.router)
app.include_router(config_router.router)
app.include_router(chat.router)


def _seed_sample_deck():
    """Create a sample deck with 3 cards on first run."""
    db = SessionLocal()
    try:
        if db.query(models.Deck).count() > 0:
            return
        deck = models.Deck(name="Sample Deck", description="Example cards to get you started")
        db.add(deck)
        db.flush()
        sample_cards = [
            ("What is the SM-2 algorithm?", "A spaced repetition algorithm that schedules reviews based on ease factor, interval, and repetition count.", "study,memory"),
            ("What does RAG stand for?", "Retrieval-Augmented Generation — combining a retrieval system with an LLM to answer questions from a knowledge base.", "ai,rag"),
            ("What is the mitochondria?", "The powerhouse of the cell; produces ATP via cellular respiration.", "biology"),
        ]
        for front, back, tags in sample_cards:
            db.add(models.Card(deck_id=deck.id, front=front, back=back, tags=tags))
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    _seed_sample_deck()
    # Ensure second_brain dirs exist
    Path("../second_brain/cards").mkdir(parents=True, exist_ok=True)
    Path("../second_brain/topics").mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
