const BASE = "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Decks
  getDecks: () => request("/decks/"),
  createDeck: (name, description = "") =>
    request("/decks/", { method: "POST", body: JSON.stringify({ name, description }) }),
  deleteDeck: (id) => request(`/decks/${id}`, { method: "DELETE" }),

  // Cards
  getCards: (deckId) => request(`/cards/deck/${deckId}`),
  getDueCards: (deckId) => request(`/cards/due/${deckId}`),
  createCard: (deckId, front, back, tags = "") =>
    request("/cards/", { method: "POST", body: JSON.stringify({ deck_id: deckId, front, back, tags }) }),
  updateCard: (cardId, deckId, front, back, tags) =>
    request(`/cards/${cardId}`, { method: "PUT", body: JSON.stringify({ deck_id: deckId, front, back, tags }) }),
  deleteCard: (id) => request(`/cards/${id}`, { method: "DELETE" }),

  // Study
  rateCard: (cardId, rating) =>
    request("/study/rate", { method: "POST", body: JSON.stringify({ card_id: cardId, rating }) }),
  aiAnswer: (cardId, userAnswer) =>
    request("/study/ai-answer", { method: "POST", body: JSON.stringify({ card_id: cardId, user_answer: userAnswer }) }),
  endSession: (answered, correct) =>
    request("/study/end-session", { method: "POST", body: JSON.stringify({ answered, correct }) }),
};
