import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function ChatSidebar({ open, onToggle }) {
  const [messages, setMessages] = useState([]); // {role, content, sources?}
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages, loading]);

  async function send(e) {
    e?.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(question, history);
      setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${err.message}`, sources: [] }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button className={`chat-toggle ${open ? "open" : ""}`} onClick={onToggle}>
        {open ? "✕" : "💬 Ask AI"}
      </button>

      <aside className={`chat-sidebar ${open ? "open" : ""}`}>
        <div className="chat-header">
          <strong>Study Assistant</strong>
          <span className="muted">Grounded in your materials</span>
        </div>

        <div className="chat-messages" ref={scrollRef}>
          {messages.length === 0 && (
            <p className="muted chat-empty">Ask anything about your lecture material.</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>
              <div className="chat-bubble">{m.content}</div>
              {m.sources && m.sources.length > 0 && (
                <div className="chat-sources">
                  {m.sources.map((s, j) => (
                    <span key={j} className="source-chip">
                      {s.source}{s.page ? ` · p.${s.page}` : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && <div className="chat-msg assistant"><div className="chat-bubble typing">…</div></div>}
        </div>

        <form className="chat-input" onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>↑</button>
        </form>
      </aside>
    </>
  );
}
