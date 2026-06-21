"""
Unit tests for RAG chunking. The invariant that matters most: NO chunk may ever
exceed MAX_CHUNK_CHARS — a chunk overflowing the embedding model's comfortable
window silently degrades retrieval quality. The overlap logic in particular is
easy to get wrong (prepending a tail can push a near-max chunk over the limit).

chromadb is stubbed so these run without the heavy vector-DB / torch deps.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub chromadb before importing rag (rag imports it at module load).
_fake = types.ModuleType("chromadb")
_utils = types.ModuleType("chromadb.utils")
_ef = types.ModuleType("chromadb.utils.embedding_functions")
_utils.embedding_functions = _ef
_fake.utils = _utils
sys.modules.setdefault("chromadb", _fake)
sys.modules.setdefault("chromadb.utils", _utils)
sys.modules.setdefault("chromadb.utils.embedding_functions", _ef)

import rag  # noqa: E402

MAX = rag.MAX_CHUNK_CHARS


def assert_all_within_max(chunks):
    for text, _page in chunks:
        assert len(text) <= MAX, f"chunk of {len(text)} chars exceeds MAX={MAX}"


def test_short_paragraphs_single_chunk_keeps_page():
    chunks = rag.chunk_segments([("Para one.\n\nPara two.\n\nPara three.", 1)])
    assert_all_within_max(chunks)
    assert all(page == 1 for _t, page in chunks)


def test_oversized_paragraph_is_hard_split_within_max():
    # 2500-char paragraph with no sentence punctuation → must hard-split.
    chunks = rag.chunk_segments([("word " * 500, 3)])
    assert len(chunks) > 1
    assert_all_within_max(chunks)


def test_overlap_does_not_overflow_near_max_pieces():
    # Regression: a near-max piece plus an overlap tail must still fit in MAX.
    chunks = rag.chunk_segments([("A" * 800, 1), ("B" * 800, 2)])
    assert_all_within_max(chunks)
    assert 1 in {page for _t, page in chunks}


def test_empty_segments_yield_no_chunks():
    assert rag.chunk_segments([("   \n\n  ", 1)]) == []
    assert rag.chunk_segments([]) == []


def test_long_sentence_stream_splits_and_stays_within_max():
    text = "".join(
        f"Sentence number {i} is here and reasonably long for testing. "
        for i in range(60)
    )
    chunks = rag.chunk_segments([(text, 1)])
    assert len(chunks) >= 2
    assert_all_within_max(chunks)


def test_first_chunk_page_is_first_paragraph_page():
    chunks = rag.chunk_segments([("Short intro.", 5)])
    assert chunks[0][1] == 5


def test_text_extraction_supported_extensions():
    assert ".pdf" in rag.SUPPORTED_EXTENSIONS
    assert ".txt" in rag.SUPPORTED_EXTENSIONS
    assert ".md" in rag.SUPPORTED_EXTENSIONS
