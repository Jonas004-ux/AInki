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
  getOverview: () => request("/decks/overview"),
  createDeck: (name, description = "") =>
    request("/decks/", { method: "POST", body: JSON.stringify({ name, description }) }),
  renameDeck: (id, name) =>
    request(`/decks/${id}/rename`, { method: "PUT", body: JSON.stringify({ name }) }),
  deleteDeck: (id) => request(`/decks/${id}`, { method: "DELETE" }),

  // Cards
  getCards: (deckId) => request(`/cards/deck/${deckId}`),
  getDueCards: (deckId) => request(`/cards/due/${deckId}`),
  browseCards: (q = "", deckId = null) =>
    request(`/cards/browse?q=${encodeURIComponent(q)}${deckId ? `&deck_id=${deckId}` : ""}`),
  createCard: (deckId, front, back, tags = "") =>
    request("/cards/", { method: "POST", body: JSON.stringify({ deck_id: deckId, front, back, tags }) }),
  updateCard: (cardId, deckId, front, back, tags) =>
    request(`/cards/${cardId}`, { method: "PUT", body: JSON.stringify({ deck_id: deckId, front, back, tags }) }),
  deleteCard: (id) => request(`/cards/${id}`, { method: "DELETE" }),
  moveCards: (cardIds, targetDeckId) =>
    request("/cards/move", { method: "POST", body: JSON.stringify({ card_ids: cardIds, target_deck_id: targetDeckId }) }),

  // Study
  rateCard: (cardId, rating) =>
    request("/study/rate", { method: "POST", body: JSON.stringify({ card_id: cardId, rating }) }),
  aiAnswer: (cardId, userAnswer) =>
    request("/study/ai-answer", { method: "POST", body: JSON.stringify({ card_id: cardId, user_answer: userAnswer }) }),
  endSession: (answered, correct) =>
    request("/study/end-session", { method: "POST", body: JSON.stringify({ answered, correct }) }),
  todayStats: () => request("/study/today"),

  // Import / export
  importCsv: (deckName, file) => {
    const form = new FormData();
    form.append("deck", deckName);
    form.append("file", file);
    return fetch(`${BASE}/import/csv`, { method: "POST", body: form }).then(async (r) => {
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Import failed");
      return r.json();
    });
  },
  exportDeckUrl: (deckId) => `${BASE}/import/export/${deckId}`,

  // Config / first-run setup
  getConfig: () => request("/config/"),
  setup: (materialsPath) =>
    request("/config/setup", { method: "POST", body: JSON.stringify({ materials_path: materialsPath }) }),
  reindex: () => request("/config/reindex", { method: "POST" }),
  indexStatus: () => request("/config/index-status"),

  // Chatbot
  chat: (question, history = []) =>
    request("/chat/", { method: "POST", body: JSON.stringify({ question, history }) }),
};
