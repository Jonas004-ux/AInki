import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function DeckView({ deck, onStudy, onBack }) {
  const [cards, setCards] = useState([]);
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [tags, setTags] = useState("");

  useEffect(() => {
    api.getCards(deck.id).then(setCards).catch(console.error);
  }, [deck.id]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!front.trim() || !back.trim()) return;
    const card = await api.createCard(deck.id, front.trim(), back.trim(), tags.trim());
    setCards((c) => [...c, card]);
    setFront(""); setBack(""); setTags("");
  }

  async function handleDelete(id) {
    await api.deleteCard(id);
    setCards((c) => c.filter((card) => card.id !== id));
  }

  return (
    <div className="page">
      <button className="btn-ghost back" onClick={onBack}>← Back</button>
      <h2>{deck.name}</h2>

      <div className="row study-buttons">
        <button onClick={() => onStudy(deck, "classic")}>Study Classic</button>
        <button onClick={() => onStudy(deck, "ai")} className="btn-ai">Study AI Mode</button>
      </div>

      <form onSubmit={handleAdd} className="card-form">
        <textarea value={front} onChange={(e) => setFront(e.target.value)} placeholder="Front (question)…" rows={2} />
        <textarea value={back} onChange={(e) => setBack(e.target.value)} placeholder="Back (answer)…" rows={2} />
        <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="Tags (comma-separated)…" />
        <button type="submit">Add Card</button>
      </form>

      <div className="card-list">
        {cards.map((card) => (
          <div key={card.id} className="card-row">
            <div>
              <p className="card-front">{card.front}</p>
              <p className="card-back muted">{card.back}</p>
              {card.tags && <p className="tags">{card.tags}</p>}
            </div>
            <button className="btn-ghost" onClick={() => handleDelete(card.id)}>✕</button>
          </div>
        ))}
        {cards.length === 0 && <p className="muted">No cards yet. Add some above.</p>}
      </div>
    </div>
  );
}
