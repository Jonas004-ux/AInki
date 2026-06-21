import { useEffect, useState } from "react";
import Home from "./pages/Home";
import DeckView from "./pages/DeckView";
import StudySession from "./pages/StudySession";
import FirstRunSetup from "./components/FirstRunSetup";
import ChatSidebar from "./components/ChatSidebar";
import { api } from "./api/client";
import "./App.css";

export default function App() {
  const [screen, setScreen] = useState("home");
  const [activeDeck, setActiveDeck] = useState(null);
  const [studyMode, setStudyMode] = useState("classic");
  const [firstRun, setFirstRun] = useState(null); // null=loading, true/false
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    api.getConfig()
      .then((cfg) => setFirstRun(cfg.first_run))
      .catch(() => setFirstRun(false)); // backend down → don't block the app
  }, []);

  function selectDeck(deck) {
    setActiveDeck(deck);
    setScreen("deck");
  }

  function startStudy(deck, mode) {
    setActiveDeck(deck);
    setStudyMode(mode);
    setScreen("study");
  }

  if (firstRun === null) {
    return <div className="page centered"><p className="muted">Loading…</p></div>;
  }

  if (firstRun) {
    return <FirstRunSetup onComplete={() => setFirstRun(false)} />;
  }

  let body;
  if (screen === "study") {
    body = <StudySession deck={activeDeck} mode={studyMode} onBack={() => setScreen("deck")} />;
  } else if (screen === "deck") {
    body = <DeckView deck={activeDeck} onStudy={startStudy} onBack={() => setScreen("home")} />;
  } else {
    body = <Home onSelectDeck={selectDeck} />;
  }

  return (
    <div className={`app-shell ${chatOpen ? "chat-open" : ""}`}>
      <div className="app-main">{body}</div>
      <ChatSidebar open={chatOpen} onToggle={() => setChatOpen((o) => !o)} />
    </div>
  );
}
