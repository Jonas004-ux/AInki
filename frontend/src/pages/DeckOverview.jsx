import { useEffect, useState } from "react";
import { api } from "../api/client";
import { buildDeckTree } from "../deckTree";

export default function DeckOverview({ onStudyDeck, onImport }) {
  const [tree, setTree] = useState([]);
  const [expanded, setExpanded] = useState(() => new Set());
  const [today, setToday] = useState(0);
  const [gearFor, setGearFor] = useState(null); // fullName whose gear menu is open

  async function refresh() {
    const [overview, t] = await Promise.all([api.getOverview(), api.todayStats()]);
    setTree(buildDeckTree(overview));
    setToday(t.studied_today);
  }
  useEffect(() => { refresh().catch(console.error); }, []);

  function toggle(fullName) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(fullName) ? next.delete(fullName) : next.add(fullName);
      return next;
    });
  }

  async function handleCreate() {
    const name = prompt("Deck name (use :: for subdecks, e.g. Biology::Cells):");
    if (name?.trim()) {
      try { await api.createDeck(name.trim()); refresh(); }
      catch (e) { alert(e.message); }
    }
  }

  async function handleRename(deck) {
    const name = prompt("Rename deck:", deck.name);
    if (name?.trim() && name.trim() !== deck.name) {
      await api.renameDeck(deck.id, name.trim()); setGearFor(null); refresh();
    }
  }

  async function handleDelete(deck) {
    if (confirm(`Delete "${deck.name}" and all its subdecks/cards?`)) {
      await api.deleteDeck(deck.id); setGearFor(null); refresh();
    }
  }

  function renderRow(node) {
    const hasChildren = node.children.length > 0;
    const isOpen = expanded.has(node.fullName);
    const { counts, deck } = node;
    const rows = [
      <div key={node.fullName} className="deck-row" style={{ paddingLeft: `${node.depth * 22 + 8}px` }}>
        <span className="deck-toggle" onClick={() => hasChildren && toggle(node.fullName)}>
          {hasChildren ? (isOpen ? "−" : "+") : ""}
        </span>
        <span className="deck-name" onClick={() => deck && onStudyDeck(deck)}>{node.label}</span>
        <span className="count count-new">{counts.new || ""}</span>
        <span className="count count-learning">{counts.learning || ""}</span>
        <span className="count count-due">{counts.due || ""}</span>
        <span className="deck-gear-cell">
          {deck && (
            <span className="deck-gear" onClick={(e) => { e.stopPropagation(); setGearFor(gearFor === node.fullName ? null : node.fullName); }}>⚙</span>
          )}
          {gearFor === node.fullName && deck && (
            <div className="gear-menu" onMouseLeave={() => setGearFor(null)}>
              <button onClick={() => onStudyDeck(deck)}>Study</button>
              <button onClick={() => handleRename(deck)}>Rename</button>
              <a href={api.exportDeckUrl(deck.id)}>Export CSV</a>
              <button className="danger" onClick={() => handleDelete(deck)}>Delete</button>
            </div>
          )}
        </span>
      </div>,
    ];
    if (hasChildren && isOpen) node.children.forEach((c) => rows.push(...renderRow(c)));
    return rows;
  }

  return (
    <div className="overview">
      <div className="deck-table">
        <div className="deck-header">
          <span className="deck-name-h">Deck</span>
          <span className="count">New</span>
          <span className="count">Learn</span>
          <span className="count">Due</span>
          <span className="deck-gear-cell" />
        </div>
        {tree.length === 0 && <p className="muted empty-decks">No decks yet. Create one below.</p>}
        {tree.flatMap(renderRow)}
      </div>

      <p className="today-line muted">
        {today > 0 ? `Studied ${today} card${today === 1 ? "" : "s"} today` : "No cards studied yet today"}
      </p>

      <div className="overview-actions">
        <button onClick={handleCreate}>Create Deck</button>
        <button onClick={onImport}>Import File</button>
      </div>
    </div>
  );
}
