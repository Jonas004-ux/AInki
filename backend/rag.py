"""
RAG engine: extract -> chunk -> embed -> ChromaDB, plus retrieval.

Extraction quality is the whole ballgame for a study chatbot, so we do PDFs
properly with PyMuPDF (page-aware text extraction) rather than punting to
"txt only." Markdown and plain text are also supported. Each chunk keeps its
source file + page so the chatbot can cite where an answer came from.

Embeddings: sentence-transformers `all-MiniLM-L6-v2` (local, no API key, 384-dim),
wired into ChromaDB's persistent client at data/chroma/.
"""
import logging
import re
from pathlib import Path
from typing import Optional

# ChromaDB 0.5.x ships a posthog telemetry shim that spams harmless errors on
# every call ("capture() takes 1 positional argument..."). Silence it.
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "lecture_materials"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Chunking parameters (characters). ~900 chars ≈ 180-220 tokens, a good
# retrieval granularity for lecture prose and slides.
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 150

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}

# In-memory indexing progress, surfaced via the /config/index-status endpoint.
index_status = {
    "state": "idle",          # idle | indexing | done | error
    "processed_files": 0,
    "total_files": 0,
    "chunk_count": 0,
    "message": "",
}


# ---------------------------------------------------------------------------
# ChromaDB client / collection
# ---------------------------------------------------------------------------

_client = None
_embed_fn = None


def _get_client():
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_embed_fn():
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
    return _embed_fn


def _get_collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=_get_embed_fn()
    )


# ---------------------------------------------------------------------------
# Extraction: (text, page) segments per file
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> list[tuple[str, Optional[int]]]:
    """Page-aware extraction with PyMuPDF. Returns [(page_text, page_number)]."""
    import fitz  # PyMuPDF

    segments: list[tuple[str, Optional[int]]] = []
    with fitz.open(path) as doc:
        for page_index in range(doc.page_count):
            text = doc[page_index].get_text("text")
            if text and text.strip():
                segments.append((text, page_index + 1))  # 1-based page numbers
    return segments


def _extract_text(path: Path) -> list[tuple[str, Optional[int]]]:
    """Plain text / markdown: a single segment, no page numbers."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [(text, None)] if text.strip() else []


def extract_file(path: Path) -> list[tuple[str, Optional[int]]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext in {".txt", ".md", ".markdown"}:
        return _extract_text(path)
    return []


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _split_paragraphs(text: str) -> list[str]:
    # Normalize whitespace and split on blank lines.
    parts = re.split(r"\n\s*\n", text)
    return [re.sub(r"[ \t]+", " ", p).strip() for p in parts if p.strip()]


def _hard_split(paragraph: str, size: int) -> list[str]:
    """Split an oversized paragraph on sentence boundaries, falling back to a
    hard character cut so no chunk ever exceeds `size`."""
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces, buf = [], ""
    for s in sentences:
        if len(s) > size:  # a single monster sentence — slice it
            if buf:
                pieces.append(buf); buf = ""
            for i in range(0, len(s), size):
                pieces.append(s[i:i + size])
        elif len(buf) + len(s) + 1 <= size:
            buf = f"{buf} {s}".strip()
        else:
            pieces.append(buf); buf = s
    if buf:
        pieces.append(buf)
    return pieces


def chunk_segments(segments: list[tuple[str, Optional[int]]]) -> list[tuple[str, Optional[int]]]:
    """Greedily pack paragraphs into ~MAX_CHUNK_CHARS chunks with overlap.
    Each emitted chunk is tagged with the page of its first paragraph."""
    chunks: list[tuple[str, Optional[int]]] = []
    buf = ""
    buf_page: Optional[int] = None

    def flush():
        nonlocal buf, buf_page
        if buf.strip():
            chunks.append((buf.strip(), buf_page))
        buf, buf_page = "", None

    for text, page in segments:
        for para in _split_paragraphs(text):
            for piece in (_hard_split(para, MAX_CHUNK_CHARS) if len(para) > MAX_CHUNK_CHARS else [para]):
                if not buf:
                    buf, buf_page = piece, page
                elif len(buf) + len(piece) + 2 <= MAX_CHUNK_CHARS:
                    buf = f"{buf}\n\n{piece}"
                else:
                    # Carry an overlap tail into the next chunk, but clamp it so
                    # tail + separator + piece never exceeds MAX_CHUNK_CHARS.
                    room = max(0, MAX_CHUNK_CHARS - len(piece) - 2)
                    n = min(CHUNK_OVERLAP_CHARS, room)
                    overlap_tail = buf[-n:] if n > 0 else ""
                    flush()
                    buf = f"{overlap_tail}\n\n{piece}".strip() if overlap_tail else piece
                    buf_page = page
    flush()
    return chunks


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def _gather_files(root: Path) -> list[Path]:
    return [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def reset_index():
    """Drop and recreate the collection so re-indexing starts clean."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


def index_materials(materials_path: str):
    """Full (re)index. Updates module-level index_status as it goes.
    Intended to run in a background task."""
    root = Path(materials_path).expanduser()
    index_status.update(state="indexing", processed_files=0, total_files=0,
                        chunk_count=0, message="Scanning folder…")

    if not root.exists() or not root.is_dir():
        index_status.update(state="error", message=f"Path not found: {materials_path}")
        return

    files = _gather_files(root)
    index_status["total_files"] = len(files)
    if not files:
        index_status.update(state="done", message="No supported files found "
                            "(.pdf, .txt, .md).")
        return

    reset_index()
    collection = _get_collection()
    total_chunks = 0

    for fi, path in enumerate(files):
        try:
            segments = extract_file(path)
            chunks = chunk_segments(segments)
            if chunks:
                rel = str(path.relative_to(root))
                ids, docs, metas = [], [], []
                for ci, (chunk_text, page) in enumerate(chunks):
                    ids.append(f"{rel}::{ci}")
                    docs.append(chunk_text)
                    metas.append({"source": rel, "page": page if page is not None else -1})
                collection.add(ids=ids, documents=docs, metadatas=metas)
                total_chunks += len(chunks)
        except Exception as e:  # one bad file shouldn't kill the whole index
            index_status["message"] = f"Skipped {path.name}: {e}"
        index_status["processed_files"] = fi + 1
        index_status["chunk_count"] = total_chunks

    index_status.update(state="done",
                        message=f"Indexed {len(files)} files, {total_chunks} chunks.")
    return {"file_count": len(files), "chunk_count": total_chunks}


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, k: int = 5) -> list[dict]:
    """Return top-k chunks: [{text, source, page, distance}]."""
    collection = _get_collection()
    if collection.count() == 0:
        return []
    res = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        page = meta.get("page", -1)
        hits.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "page": None if page == -1 else page,
            "distance": dist,
        })
    return hits
