import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";

// Kartenverwaltung — Anki's Card Browser: a searchable table of every card,
// with inline edit, bulk move, and delete.
export default function CardBrowser() {
  const [rows, setRows] = useState([]);
  const [decks, setDecks] = useState([]);
  const [q, setQ] = useState("");
  const [deckFilter, setDeckFilter] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [editing, setEditing] = useState(null); // card id
  const [draft, setDraft] = useState({ front: "", back: "", tags: "" });

  const load = useCallback(async () => {
    const data = await api.browseCards(q, deckFilter || null);
    setRows(data);
    setSelected(new Set());
  }, [q, deckFilter]);

  useEffect(() => { api.getDecks().then(setDecks); }, []);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  function toggleSel(id) {
    setSelected((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  function startEdit(r) {
    setEditing(r.id);
    setDraft({ front: r.front, back: r.back, tags: r.tags });
  }
  async function saveEdit(r) {
    await api.updateCard(r.id, r.deck_id, draft.front, draft.back, draft.tags);
    setEditing(null); load();
  }
  async function del(id) {
    if (confirm("Delete this card?")) { await api.deleteCard(id); load(); }
  }
  async function bulkMove(targetId) {
    if (!targetId || selected.size === 0) return;
    await api.moveCards([...selected], Number(targetId));
    load();
  }
  async function bulkDelete() {
    if (selected.size && confirm(`Delete ${selected.size} card(s)?`)) {
      for (const id of selected) await api.deleteCard(id);
      load();
    }
  }

  const stateLabel = { new: "New", learning: "Learn", due: "Due", not_due: "—" };

  return (
    <div className="browser">
      <div className="browser-toolbar">
        <input className="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search front, back, tags…" />
        <select value={deckFilter} onChange={(e) => setDeckFilter(e.target.value)}>
          <option value="">All decks</option>
          {decks.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        {selected.size > 0 && (
          <div className="bulk-actions">
            <span className="muted">{selected.size} selected</span>
            <select defaultValue="" onChange={(e) => { bulkMove(e.target.value); e.target.value = ""; }}>
              <option value="" disabled>Move to…</option>
              {decks.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <button className="danger" onClick={bulkDelete}>Delete</button>
          </div>
        )}
      </div>

      <div className="browser-table">
        <div className="browser-row browser-head">
          <span className="col-check" />
          <span className="col-front">Front</span>
          <span className="col-back">Back</span>
          <span className="col-deck">Deck</span>
          <span className="col-tags">Tags</span>
          <span className="col-state">State</span>
          <span className="col-act" />
        </div>
        {rows.map((r) => (
          editing === r.id ? (
            <div key={r.id} className="browser-row editing">
              <span className="col-check" />
              <textarea className="col-front" value={draft.front} onChange={(e) => setDraft({ ...draft, front: e.target.value })} rows={2} />
              <textarea className="col-back" value={draft.back} onChange={(e) => setDraft({ ...draft, back: e.target.value })} rows={2} />
              <span className="col-deck muted">{r.deck_name}</span>
              <input className="col-tags" value={draft.tags} onChange={(e) => setDraft({ ...draft, tags: e.target.value })} />
              <span className="col-state" />
              <span className="col-act">
                <button onClick={() => saveEdit(r)}>Save</button>
                <button className="btn-ghost" onClick={() => setEditing(null)}>✕</button>
              </span>
            </div>
          ) : (
            <div key={r.id} className="browser-row">
              <span className="col-check"><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSel(r.id)} /></span>
              <span className="col-front" onClick={() => startEdit(r)}>{r.front}</span>
              <span className="col-back muted" onClick={() => startEdit(r)}>{r.back}</span>
              <span className="col-deck muted">{r.deck_name}</span>
              <span className="col-tags">{r.tags && <span className="tags">{r.tags}</span>}</span>
              <span className={`col-state state-${r.state}`}>{stateLabel[r.state]}</span>
              <span className="col-act"><button className="btn-ghost" onClick={() => del(r.id)}>✕</button></span>
            </div>
          )
        ))}
        {rows.length === 0 && <p className="muted empty-decks">No cards match.</p>}
      </div>
      <p className="muted browser-count">{rows.length} card{rows.length === 1 ? "" : "s"}</p>
    </div>
  );
}
