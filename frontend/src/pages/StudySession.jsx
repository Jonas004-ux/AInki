import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";

const RATING_LABELS = ["Again", "Hard", "Good", "Easy"];

export default function StudySession({ deck, mode, onBack }) {
  const [queue, setQueue] = useState([]);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [aiAnswer, setAiAnswer] = useState("");
  const [aiResult, setAiResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [stats, setStats] = useState({ answered: 0, correct: 0 });

  useEffect(() => {
    api.getDueCards(deck.id).then((cards) => {
      setQueue(cards);
      if (cards.length === 0) setDone(true);
    });
  }, [deck.id]);

  const advance = useCallback(() => {
    setFlipped(false);
    setAiAnswer("");
    setAiResult(null);
    if (idx + 1 >= queue.length) {
      setDone(true);
    } else {
      setIdx((i) => i + 1);
    }
  }, [idx, queue.length]);

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e) {
      if (mode === "classic") {
        if (e.code === "Space" && !flipped) { e.preventDefault(); setFlipped(true); }
        if (flipped) {
          if (e.key === "1") handleRate(0);
          if (e.key === "2") handleRate(1);
          if (e.key === "3") handleRate(2);
          if (e.key === "4") handleRate(3);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flipped, mode, idx]);

  async function handleRate(rating) {
    await api.rateCard(queue[idx].id, rating);
    advance();
  }

  async function handleAiSubmit() {
    if (!aiAnswer.trim()) return;
    setLoading(true);
    try {
      const result = await api.aiAnswer(queue[idx].id, aiAnswer);
      setAiResult(result);
      setStats((s) => ({
        answered: s.answered + 1,
        correct: s.correct + (result.rating >= 2 ? 1 : 0),
      }));
    } catch (err) {
      setAiResult({ verdict: "error", feedback: err.message, rating: 0 });
    } finally {
      setLoading(false);
    }
  }

  // When an AI-mode session ends, fire the batched Second Brain writes once.
  useEffect(() => {
    if (done && mode === "ai" && stats.answered > 0) {
      api.endSession(stats.answered, stats.correct).catch(console.error);
    }
  }, [done, mode, stats.answered, stats.correct]);

  if (done) return (
    <div className="page centered">
      <h2>Session complete! 🎉</h2>
      <p className="muted">All due cards reviewed.</p>
      <button onClick={onBack}>Back to Deck</button>
    </div>
  );

  if (queue.length === 0) return <div className="page centered"><p>Loading…</p></div>;

  const card = queue[idx];

  return (
    <div className="page study">
      <div className="study-header">
        <button className="btn-ghost" onClick={onBack}>← Back</button>
        <span className="muted">{idx + 1} / {queue.length}</span>
        <span className={`mode-badge ${mode}`}>{mode === "ai" ? "AI Mode" : "Classic"}</span>
      </div>

      <div className={`flashcard ${flipped ? "flipped" : ""}`} onClick={() => mode === "classic" && setFlipped(true)}>
        <div className="flashcard-inner">
          <div className="flashcard-front"><p>{card.front}</p></div>
          <div className="flashcard-back"><p>{card.back}</p></div>
        </div>
      </div>

      {mode === "classic" && (
        <>
          {!flipped && <p className="hint muted">Space to flip</p>}
          {flipped && (
            <div className="rating-buttons">
              {RATING_LABELS.map((label, i) => (
                <button key={i} className={`rating-btn rating-${i}`} onClick={() => handleRate(i)}>
                  {i + 1} {label}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {mode === "ai" && (
        <div className="ai-panel">
          {!aiResult ? (
            <>
              <textarea
                value={aiAnswer}
                onChange={(e) => setAiAnswer(e.target.value)}
                placeholder="Type your answer…"
                rows={4}
                disabled={loading}
              />
              <button onClick={handleAiSubmit} disabled={loading || !aiAnswer.trim()}>
                {loading ? "Evaluating…" : "Submit Answer"}
              </button>
            </>
          ) : (
            <div className={`ai-result verdict-${aiResult.verdict}`}>
              <p className="verdict">{aiResult.verdict === "correct" ? "✅ Correct" : aiResult.verdict === "partial" ? "⚠️ Partial" : "❌ Incorrect"}</p>
              <p>{aiResult.feedback}</p>
              <div className="flashcard-reveal"><strong>Answer:</strong> {card.back}</div>
              <button onClick={advance}>Next →</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
