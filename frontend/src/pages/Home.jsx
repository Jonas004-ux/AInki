import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Home({ onSelectDeck }) {
  const [decks, setDecks] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDecks().then(setDecks).catch(console.error);
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const deck = await api.createDeck(name.trim());
      setDecks((d) => [...d, deck]);
      setName("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    await api.deleteDeck(id);
    setDecks((d) => d.filter((deck) => deck.id !== id));
  }

  return (
    <div className="page">
      <h1>AInki</h1>
      <p className="subtitle">AI-powered spaced repetition</p>

      <form onSubmit={handleCreate} className="row">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New deck name…"
        />
        <button type="submit">Create Deck</button>
      </form>
      {error && <p className="error">{error}</p>}

      <div className="deck-list">
        {decks.map((deck) => (
          <div key={deck.id} className="deck-card">
            <div onClick={() => onSelectDeck(deck)} className="deck-info">
              <strong>{deck.name}</strong>
              <span>{deck.card_count} cards</span>
            </div>
            <button className="btn-ghost" onClick={() => handleDelete(deck.id)}>✕</button>
          </div>
        ))}
        {decks.length === 0 && <p className="muted">No decks yet. Create one above.</p>}
      </div>
    </div>
  );
}
