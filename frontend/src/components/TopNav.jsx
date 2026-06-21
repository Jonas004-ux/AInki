const TABS = [
  { key: "overview", label: "Decks" },
  { key: "add", label: "Add" },
  { key: "browse", label: "Browse" },
  { key: "stats", label: "Statistics" },
  { key: "sync", label: "Sync" },
];

export default function TopNav({ active, onChange }) {
  return (
    <nav className="topnav">
      <div className="topnav-brand">AInki</div>
      <div className="topnav-tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`topnav-tab ${active === t.key ? "active" : ""}`}
            onClick={() => onChange(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
