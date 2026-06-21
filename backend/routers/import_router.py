"""
Flashcard import/export.

Import accepts CSV/TSV text (the format Anki exports to and most quizlet-style
exports use): one card per line, columns = front, back, [tags]. Delimiter is
auto-detected (tab or comma). Lines starting with '#' (Anki's metadata header)
are skipped. Cards land in a chosen deck (created if missing, '::' subdecks ok).
"""
import csv
import io
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/import", tags=["import"])

SEP = "::"


def _get_or_create_deck(name: str, db: Session) -> models.Deck:
    name = name.strip()
    deck = db.query(models.Deck).filter(models.Deck.name == name).first()
    if deck:
        return deck
    # Ensure parent decks exist for '::' paths.
    parts = name.split(SEP)
    for i in range(1, len(parts)):
        prefix = SEP.join(parts[:i])
        if not db.query(models.Deck).filter(models.Deck.name == prefix).first():
            db.add(models.Deck(name=prefix, description=""))
    deck = models.Deck(name=name, description="")
    db.add(deck)
    db.flush()
    return deck


def _detect_delimiter(sample: str) -> str:
    # Prefer tab (Anki default); fall back to comma.
    first = next((l for l in sample.splitlines() if l and not l.startswith("#")), "")
    return "\t" if first.count("\t") >= first.count(",") and "\t" in first else ","


@router.post("/csv")
async def import_csv(
    deck: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    raw = (await file.read()).decode("utf-8", errors="ignore")
    if not raw.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    delimiter = _detect_delimiter(raw)
    target = _get_or_create_deck(deck, db)

    imported, skipped = 0, 0
    reader = csv.reader(io.StringIO(raw), delimiter=delimiter)
    for row in reader:
        if not row or (row[0].startswith("#")):
            continue
        cells = [c.strip() for c in row]
        if len(cells) < 2 or not cells[0] or not cells[1]:
            skipped += 1
            continue
        front, back = cells[0], cells[1]
        tags = cells[2] if len(cells) >= 3 else ""
        # Normalize Anki space-separated tags to our comma-separated storage.
        tags = ",".join(t for t in tags.replace(",", " ").split()) if tags else ""
        db.add(models.Card(deck_id=target.id, front=front, back=back, tags=tags))
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped, "deck": target.name, "deck_id": target.id}


@router.get("/export/{deck_id}", response_class=PlainTextResponse)
def export_csv(deck_id: int, db: Session = Depends(get_db)):
    """Export a deck (and its subdecks) to CSV: front,back,tags."""
    deck = db.query(models.Deck).filter(models.Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck_ids = [deck.id] + [
        s.id for s in db.query(models.Deck).filter(models.Deck.name.like(f"{deck.name}{SEP}%")).all()
    ]
    cards = db.query(models.Card).filter(models.Card.deck_id.in_(deck_ids)).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    for c in cards:
        writer.writerow([c.front, c.back, (c.tags or "").replace(",", " ")])
    return PlainTextResponse(
        buf.getvalue(),
        headers={"Content-Disposition": f'attachment; filename="{deck.name}.csv"'},
    )
