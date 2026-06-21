import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

// Datei importieren — import CSV/TSV flashcards (front, back, [tags]) into a deck.
export default function ImportCards({ onDone }) {
  const [decks, setDecks] = useState([]);
  const [deckName, setDeckName] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => { api.getDecks().then(setDecks); }, []);

  async function handleImport(e) {
    e.preventDefault();
    setError(""); setResult(null);
    if (!deckName.trim() || !file) { setError("Pick a deck name and a file."); return; }
    setBusy(true);
    try {
      const r = await api.importCsv(deckName.trim(), file);
      setResult(r);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-page">
      <h2>Import Flashcards</h2>
      <p className="muted">
        CSV or TSV, one card per line: <code>front, back, tags</code> (tags optional).
        Tab- or comma-separated; <code>#</code> comment lines are skipped — compatible with Anki text exports.
      </p>

      <form onSubmit={handleImport} className="card-form">
        <label>Target deck (type a new name or pick existing; use :: for subdecks)</label>
        <input
          list="deck-options"
          value={deckName}
          onChange={(e) => setDeckName(e.target.value)}
          placeholder="e.g. Biology::Cells"
        />
        <datalist id="deck-options">
          {decks.map((d) => <option key={d.id} value={d.name} />)}
        </datalist>

        <label>File (.csv / .tsv / .txt)</label>
        <input ref={fileRef} type="file" accept=".csv,.tsv,.txt" onChange={(e) => setFile(e.target.files[0])} />

        <div className="form-actions">
          <button type="submit" disabled={busy}>{busy ? "Importing…" : "Import"}</button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {result && (
        <div className="import-result">
          <p className="success-text">
            ✅ Imported {result.imported} card{result.imported === 1 ? "" : "s"} into “{result.deck}”
            {result.skipped > 0 && <span className="muted"> ({result.skipped} skipped)</span>}
          </p>
          <button onClick={onDone}>Back to Decks</button>
        </div>
      )}
    </div>
  );
}
