import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function AddCard() {
  const [decks, setDecks] = useState([]);
  const [deckId, setDeckId] = useState("");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [tags, setTags] = useState("");
  const [flash, setFlash] = useState("");

  useEffect(() => {
    api.getDecks().then((d) => {
      setDecks(d);
      if (d.length) setDeckId(String(d[0].id));
    });
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    if (!deckId || !front.trim() || !back.trim()) return;
    await api.createCard(Number(deckId), front.trim(), back.trim(), tags.trim());
    setFront(""); setBack(""); // keep deck + tags for fast entry
    setFlash("Card added ✓");
    setTimeout(() => setFlash(""), 1500);
  }

  return (
    <div className="form-page">
      <h2>Add Card</h2>
      <form onSubmit={handleAdd} className="card-form">
        <label>Deck</label>
        <select value={deckId} onChange={(e) => setDeckId(e.target.value)}>
          {decks.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <label>Front</label>
        <textarea value={front} onChange={(e) => setFront(e.target.value)} rows={3} autoFocus />
        <label>Back</label>
        <textarea value={back} onChange={(e) => setBack(e.target.value)} rows={3} />
        <label>Tags (comma-separated)</label>
        <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="biology, cells" />
        <div className="form-actions">
          <button type="submit">Add</button>
          {flash && <span className="success-text">{flash}</span>}
        </div>
      </form>
    </div>
  );
}
