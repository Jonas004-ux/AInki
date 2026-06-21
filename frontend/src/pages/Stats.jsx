import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Stats() {
  const [overview, setOverview] = useState([]);
  const [today, setToday] = useState(0);

  useEffect(() => {
    Promise.all([api.getOverview(), api.todayStats()])
      .then(([o, t]) => { setOverview(o); setToday(t.studied_today); })
      .catch(console.error);
  }, []);

  const totals = overview.reduce(
    (acc, d) => ({ new: acc.new + d.new, learning: acc.learning + d.learning, due: acc.due + d.due }),
    { new: 0, learning: 0, due: 0 }
  );

  return (
    <div className="form-page">
      <h2>Statistics</h2>
      <div className="stat-cards">
        <div className="stat-card"><span className="stat-num">{today}</span><span className="muted">studied today</span></div>
        <div className="stat-card"><span className="stat-num count-new">{totals.new}</span><span className="muted">new</span></div>
        <div className="stat-card"><span className="stat-num count-learning">{totals.learning}</span><span className="muted">learning</span></div>
        <div className="stat-card"><span className="stat-num count-due">{totals.due}</span><span className="muted">due</span></div>
      </div>

      <h3 className="stat-sub">Per deck</h3>
      <div className="deck-table">
        <div className="deck-header">
          <span className="deck-name-h">Deck</span>
          <span className="count">New</span>
          <span className="count">Learn</span>
          <span className="count">Due</span>
        </div>
        {overview.map((d) => (
          <div key={d.id} className="deck-row">
            <span className="deck-name" style={{ cursor: "default" }}>{d.name}</span>
            <span className="count count-new">{d.new || ""}</span>
            <span className="count count-learning">{d.learning || ""}</span>
            <span className="count count-due">{d.due || ""}</span>
          </div>
        ))}
      </div>
      <p className="muted" style={{ marginTop: "1.5rem" }}>
        AI-mode performance (weak topics, accuracy) is written to your <code>second_brain/</code> folder after each AI study session.
      </p>
    </div>
  );
}
