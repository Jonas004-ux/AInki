from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    tags = Column(String, default="")  # comma-separated

    # SM-2 fields
    easiness = Column(Float, default=2.5)       # EF: ease factor
    interval = Column(Integer, default=1)        # days until next review
    repetitions = Column(Integer, default=0)     # consecutive correct answers
    due_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_reviewed = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck = relationship("Deck", back_populates="cards")
