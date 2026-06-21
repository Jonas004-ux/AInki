# AInki

AI-powered spaced repetition flashcard app. Study smarter with SM-2 scheduling and AI answer evaluation.

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key (for AI Answer Mode)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. A sample deck is created automatically on first launch.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

## Study Modes

**Classic Mode** — Flip the card, self-rate with Again / Hard / Good / Easy (or keys 1–4). Space to flip.

**AI Mode** — Type your answer in free text. Claude evaluates it, gives feedback, and rates the card automatically.

## Second Brain

After every AI-mode answer, performance notes are written to `second_brain/`:
- `cards/{id}.md` — per-card answer history and AI observations
- `topics/{tag}.md` — topic-level accuracy and weak spot summaries

## SM-2 Algorithm

Cards are scheduled using the SM-2 spaced repetition algorithm ([`sm2.py`](backend/sm2.py)):
- Correct answers increase the interval exponentially based on an ease factor (EF)
- Incorrect answers reset the interval to 1 day (but EF keeps its accumulated drift)
- EF is updated after each answer and clamped to a minimum of 1.3

The math is covered by unit tests (EF drift, interval progression, reset-on-failure):

```bash
cd backend && pytest
```

## Second Brain write strategy

To keep AI-mode answers cheap, topic files are **not** rewritten on every answer.
Each answer appends one line to a per-topic JSONL log (`topics/{slug}.jsonl`), and the
human-readable `topics/{slug}.md` + `overview.md` are regenerated in a single batch at
session end (`/study/end-session`). Card files are small (one per card) and rewritten in place.

## First-run setup

On first launch the app asks for the folder containing your lecture materials. The
path is saved to `data/config.json` and indexing starts immediately (you can also
re-index later via `POST /config/reindex`). A sample deck is seeded so the UI isn't empty.

## RAG / Chatbot

The chatbot ("Ask AI" sidebar) answers questions grounded in your own lecture material.

**Pipeline** ([`rag.py`](backend/rag.py)):
1. **Extract** — PDFs via **PyMuPDF** (page-aware), plus `.txt` / `.md`. Each chunk keeps its source file and page so answers can cite where they came from.
2. **Chunk** — paragraphs greedily packed into ~900-char chunks with 150-char overlap; oversized paragraphs are sentence/hard-split. No chunk ever exceeds the limit (unit-tested).
3. **Embed** — `all-MiniLM-L6-v2` via sentence-transformers (local, no API key).
4. **Store** — ChromaDB persistent client at `data/chroma/`.
5. **Retrieve + answer** — top-k chunks are fed to Claude (`claude-sonnet-4-6`), which answers and cites the excerpts used.

Chunking has its own unit tests (`pytest tests/test_rag_chunking.py`) — the key invariant is that no chunk overflows the embedding window, since that silently degrades retrieval.
