"""
Writes performance files after AI-mode answers.

Write strategy (important for cost/perf):
  - Card files (cards/{id}.md): one file per card, bounded size. The AI Observations
    section is rewritten each answer (it's a running note), so a read+rewrite is
    unavoidable but cheap — each file only ever holds one card's history.
  - Topic files aggregate across MANY cards, so rewriting them from scratch on every
    answer gets expensive fast. Instead we APPEND one structured line to a per-topic
    JSONL log on the hot path (O(1), no read), and regenerate the human-readable
    topics/{slug}.md only in batch at session end (regenerate_topic_files).
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from models import Card

SECOND_BRAIN_ROOT = Path(__file__).parent.parent / "second_brain"
RATING_LABELS = {0: "Again", 1: "Hard", 2: "Good", 3: "Easy"}
VERDICT_ICONS = {0: "❌", 1: "⚠️", 2: "✅", 3: "✅"}


def _card_path(card_id: int) -> Path:
    return SECOND_BRAIN_ROOT / "cards" / f"{card_id}.md"


def _slug(tag: str) -> str:
    return tag.strip().lower().replace(" ", "_")


def _topic_md_path(tag: str) -> Path:
    return SECOND_BRAIN_ROOT / "topics" / f"{_slug(tag)}.md"


def _topic_log_path(tag: str) -> Path:
    return SECOND_BRAIN_ROOT / "topics" / f"{_slug(tag)}.jsonl"


def _ensure_dirs():
    (SECOND_BRAIN_ROOT / "cards").mkdir(parents=True, exist_ok=True)
    (SECOND_BRAIN_ROOT / "topics").mkdir(parents=True, exist_ok=True)


def card_tags(card: Card) -> list[str]:
    return [t.strip() for t in (card.tags or "").split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Hot path: called once per AI-mode answer
# ---------------------------------------------------------------------------

def update_card_file(card: Card, user_answer: str, rating: int, ai_notes: str):
    """Read+rewrite the single card file. Bounded size; acceptable per-answer."""
    _ensure_dirs()
    path = _card_path(card.id)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    verdict = VERDICT_ICONS[rating]
    rating_label = RATING_LABELS[rating]
    summary = user_answer[:80].replace("|", "/").replace("\n", " ")
    notes = ai_notes[:60].replace("|", "/").replace("\n", " ")
    new_row = f"| {date} | \"{summary}\" | {verdict} {rating_label} | {rating_label} | {notes} |"

    if path.exists():
        lines = path.read_text().split("\n")
        insert_idx = next((i + 1 for i, l in enumerate(lines) if l.startswith("|---")), None)
        if insert_idx:
            lines.insert(insert_idx, new_row)
        # Refresh the AI Observations section (running note) with the latest note.
        obs_idx = next((i for i, l in enumerate(lines) if l.startswith("## AI Observations")), None)
        if obs_idx is not None and obs_idx + 1 < len(lines):
            lines[obs_idx + 1] = ai_notes
        content = "\n".join(lines)
    else:
        deck_name = card.deck.name if card.deck else "Unknown"
        content = f"""# Card: {card.front[:60]}

**Deck:** {deck_name}
**Tags:** {card.tags or ""}
**Card ID:** {card.id}

## Performance Log

| Date | User Answer (summary) | AI Verdict | Rating | Notes |
|------|----------------------|------------|--------|-------|
{new_row}

## AI Observations
{ai_notes}
"""
    path.write_text(content)


def log_topic_answer(tag: str, card: Card, rating: int):
    """Append-only: one JSONL line per answer. No read, no full rewrite."""
    _ensure_dirs()
    record = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "card_id": card.id,
        "card_front": card.front[:60],
        "rating": rating,
    }
    with _topic_log_path(tag).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Batch: called at session end
# ---------------------------------------------------------------------------

def _read_topic_log(tag: str) -> list[dict]:
    path = _topic_log_path(tag)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def regenerate_topic_file(tag: str, cards: list[Card]):
    """Recompute topics/{slug}.md from the append-only log + current card states.

    `cards` is every card currently carrying this tag (for due dates / last rating).
    """
    _ensure_dirs()
    records = _read_topic_log(tag)
    total = len(records)
    correct = sum(1 for r in records if r["rating"] >= 2)
    needs_work = total - correct
    accuracy = round(100 * correct / total) if total else 0

    # Last rating per card from the log
    last_rating = {}
    for r in records:
        last_rating[r["card_id"]] = r["rating"]

    card_lines = []
    for c in cards:
        lr = last_rating.get(c.id)
        lr_label = RATING_LABELS[lr] if lr is not None else "—"
        due = c.due_date.strftime("%Y-%m-%d") if c.due_date else "N/A"
        card_lines.append(
            f"- [{c.front[:60]}](../cards/{c.id}.md) — last rating: {lr_label} — due: {due}"
        )

    content = f"""# Topic: {tag.strip().title()}

## Performance Summary
- Total answers: {total}
- Correct (Good/Easy): {correct}
- Needs work (Again/Hard): {needs_work}
- Accuracy rate: {accuracy}%

## Cards in this Topic
{chr(10).join(card_lines) if card_lines else "_No cards yet._"}

## Weak Spots Identified
_AI will populate this as more answers come in._

## Recommended Focus
_AI will populate this as more answers come in._
"""
    _topic_md_path(tag).write_text(content)


def topic_accuracy(tag: str) -> tuple[int, int]:
    """(total_answers, accuracy_pct) computed from the log. Used by overview."""
    records = _read_topic_log(tag)
    total = len(records)
    if not total:
        return 0, 0
    correct = sum(1 for r in records if r["rating"] >= 2)
    return total, round(100 * correct / total)


def write_overview(weak_topics: list[tuple[str, int, int]], session_stats: dict):
    """overview.md — top weak topics + session stats. Called at session end.

    weak_topics: list of (tag, total_answers, accuracy_pct), already sorted weakest-first.
    """
    _ensure_dirs()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    weak_lines = [
        f"- **{tag.title()}** — {acc}% accuracy ({total} answers)"
        for tag, total, acc in weak_topics[:3]
    ] or ["_No topic data yet._"]

    content = f"""# Study Overview

_Last updated: {date}_

## Top 3 Weakest Topics
{chr(10).join(weak_lines)}

## Session Stats
- Cards answered this session: {session_stats.get("answered", 0)}
- Correct: {session_stats.get("correct", 0)}
- Needs work: {session_stats.get("needs_work", 0)}

## Recommended Next
_AI will populate this based on your weakest topics._
"""
    (SECOND_BRAIN_ROOT / "overview.md").write_text(content)
