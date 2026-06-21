import { useEffect, useState } from "react";
import { api } from "../api/client";

// Synchronisieren — manage the lecture-material RAG index that powers the chatbot.
export default function Sync() {
  const [cfg, setCfg] = useState(null);
  const [path, setPath] = useState("");
  const [status, setStatus] = useState(null);
  const [polling, setPolling] = useState(false);

  async function refresh() {
    const c = await api.getConfig();
    setCfg(c);
    setPath(c.materials_path || "");
  }
  useEffect(() => { refresh().catch(console.error); }, []);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(async () => {
      const s = await api.indexStatus();
      setStatus(s);
      if (s.state === "done" || s.state === "error") { setPolling(false); refresh(); }
    }, 1000);
    return () => clearInterval(id);
  }, [polling]);

  async function startIndex() {
    if (!path.trim()) return;
    await api.setup(path.trim());
    setPolling(true);
  }
  async function reindex() {
    await api.reindex();
    setPolling(true);
  }

  return (
    <div className="form-page">
      <h2>Materials & Sync</h2>
      <p className="muted">
        Index your lecture materials (PDF, .txt, .md) so the <strong>Ask AI</strong> chatbot can answer from your own notes.
      </p>

      <div className="card-form">
        <label>Materials folder path</label>
        <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="/Users/you/Documents/Lectures" />
        <div className="form-actions">
          <button onClick={startIndex}>Set & Index</button>
          {cfg?.materials_path && <button className="btn-ghost" onClick={reindex}>Re-index</button>}
        </div>
      </div>

      {cfg && cfg.materials_path && (
        <p className="muted">
          Indexed: <strong>{cfg.file_count}</strong> files · <strong>{cfg.chunk_count}</strong> chunks
          {cfg.indexed_at && <> · {new Date(cfg.indexed_at).toLocaleString()}</>}
        </p>
      )}

      {status && status.state === "indexing" && (
        <div className="index-progress">
          <p>{status.processed_files} / {status.total_files} files · {status.chunk_count} chunks</p>
          <p className="muted">{status.message}</p>
        </div>
      )}
      {status && status.state === "done" && <p className="success-text">✅ {status.message}</p>}
      {status && status.state === "error" && <p className="error">{status.message}</p>}
    </div>
  );
}
