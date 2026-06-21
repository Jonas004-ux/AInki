"""
RAG chatbot: retrieve relevant lecture chunks, then answer with Claude,
grounded in those chunks and citing sources.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import rag

router = APIRouter(prefix="/chat", tags=["chat"])

CHAT_MODEL = "claude-sonnet-4-6"
TOP_K = 5


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class Source(BaseModel):
    source: str
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


def _build_context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        loc = h["source"] + (f" (p.{h['page']})" if h["page"] else "")
        blocks.append(f"[{i}] {loc}\n{h['text']}")
    return "\n\n".join(blocks)


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest):
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    hits = rag.retrieve(payload.question, k=TOP_K)

    if not hits:
        context_note = (
            "No lecture material has been indexed yet (or nothing matched). "
            "Answer from general knowledge, and tell the student their materials "
            "aren't indexed."
        )
        context = ""
    else:
        context_note = (
            "Answer the student's question using ONLY the lecture excerpts below "
            "when they are relevant. Cite the excerpt numbers you used like [1], [2]. "
            "If the excerpts don't cover it, say so and answer from general knowledge."
        )
        context = "\n\nLecture excerpts:\n" + _build_context(hits)

    system_prompt = (
        "You are AInki's study assistant. You help a student understand their "
        "lecture material. Be concise, accurate, and pedagogical. " + context_note + context
    )

    # Recent conversation history (cap to keep the prompt small)
    messages = [{"role": m.role, "content": m.content} for m in payload.history[-6:]]
    messages.append({"role": "user", "content": payload.question})

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    # De-duplicate sources, preserving order
    seen, sources = set(), []
    for h in hits:
        key = (h["source"], h["page"])
        if key not in seen:
            seen.add(key)
            sources.append(Source(source=h["source"], page=h["page"]))

    return ChatResponse(answer=msg.content[0].text, sources=sources)
