import { useEffect, useState } from "react";
import TopNav from "./components/TopNav";
import DeckOverview from "./pages/DeckOverview";
import AddCard from "./pages/AddCard";
import CardBrowser from "./pages/CardBrowser";
import Stats from "./pages/Stats";
import Sync from "./pages/Sync";
import ImportCards from "./pages/ImportCards";
import StudySession from "./pages/StudySession";
import FirstRunSetup from "./components/FirstRunSetup";
import ChatSidebar from "./components/ChatSidebar";
import { api } from "./api/client";
import "./App.css";

export default function App() {
  const [tab, setTab] = useState("overview");
  const [firstRun, setFirstRun] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [studyDeck, setStudyDeck] = useState(null);   // deck being studied
  const [studyMode, setStudyMode] = useState(null);   // "classic" | "ai" | null
  const [chooserDeck, setChooserDeck] = useState(null); // deck awaiting mode choice

  useEffect(() => {
    api.getConfig().then((c) => setFirstRun(c.first_run)).catch(() => setFirstRun(false));
  }, []);

  if (firstRun === null) {
    return <div className="page centered"><p className="muted">Loading…</p></div>;
  }
  if (firstRun) {
    return <FirstRunSetup onComplete={() => setFirstRun(false)} />;
  }

  // Full-screen study session
  if (studyDeck && studyMode) {
    return (
      <StudySession
        deck={studyDeck}
        mode={studyMode}
        onBack={() => { setStudyDeck(null); setStudyMode(null); }}
      />
    );
  }

  let body;
  if (tab === "overview") body = <DeckOverview onStudyDeck={setChooserDeck} onImport={() => setTab("import")} />;
  else if (tab === "add") body = <AddCard />;
  else if (tab === "browse") body = <CardBrowser />;
  else if (tab === "stats") body = <Stats />;
  else if (tab === "sync") body = <Sync />;
  else if (tab === "import") body = <ImportCards onDone={() => setTab("overview")} />;

  return (
    <div className={`app-shell ${chatOpen ? "chat-open" : ""}`}>
      <TopNav active={tab === "import" ? "overview" : tab} onChange={setTab} />
      <div className="app-main">{body}</div>
      <ChatSidebar open={chatOpen} onToggle={() => setChatOpen((o) => !o)} />

      {chooserDeck && (
        <div className="modal-overlay" onClick={() => setChooserDeck(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Study “{chooserDeck.name}”</h3>
            <p className="muted">Choose a mode:</p>
            <div className="mode-choices">
              <button onClick={() => { setStudyDeck(chooserDeck); setStudyMode("classic"); setChooserDeck(null); }}>
                Classic
                <span className="mode-sub">Flip & self-rate</span>
              </button>
              <button className="btn-ai" onClick={() => { setStudyDeck(chooserDeck); setStudyMode("ai"); setChooserDeck(null); }}>
                AI Mode
                <span className="mode-sub">Type your answer, AI grades it</span>
              </button>
            </div>
            <button className="btn-ghost" onClick={() => setChooserDeck(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
