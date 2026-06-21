import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function FirstRunSetup({ onComplete }) {
  const [path, setPath] = useState("");
  const [phase, setPhase] = useState("input"); // input | indexing | error
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!path.trim()) return;
    setError("");
    try {
      await api.setup(path.trim());
      setPhase("indexing");
    } catch (err) {
      setError(err.message);
    }
  }

  // Poll indexing status while indexing
  useEffect(() => {
    if (phase !== "indexing") return;
    const id = setInterval(async () => {
      const s = await api.indexStatus();
      setStatus(s);
      if (s.state === "done") {
        clearInterval(id);
        setTimeout(onComplete, 800);
      } else if (s.state === "error") {
        clearInterval(id);
        setPhase("error");
        setError(s.message);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [phase, onComplete]);

  return (
    <div className="page centered">
      <h1>Welcome to AInki</h1>

      {phase === "input" && (
        <>
          <p className="muted">Point AInki at the folder with your lecture materials (PDFs, .txt, .md). We'll index it so the AI chatbot can answer from your notes.</p>
          <form onSubmit={handleSubmit} className="row" style={{ maxWidth: 480, width: "100%" }}>
            <input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/Users/you/Documents/Lectures"
              autoFocus
            />
            <button type="submit">Index</button>
          </form>
          {error && <p className="error">{error}</p>}
          <button className="btn-ghost" onClick={onComplete}>Skip for now</button>
        </>
      )}

      {phase === "indexing" && (
        <>
          <p className="muted">Indexing your materials…</p>
          {status && (
            <div className="index-progress">
              <p>{status.processed_files} / {status.total_files} files</p>
              <p className="muted">{status.chunk_count} chunks · {status.message}</p>
              {status.state === "done" && <p className="success-text">✅ Done!</p>}
            </div>
          )}
        </>
      )}

      {phase === "error" && (
        <>
          <p className="error">{error}</p>
          <button onClick={() => setPhase("input")}>Try again</button>
        </>
      )}
    </div>
  );
}
