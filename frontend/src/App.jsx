import { useState } from "react";
import Home from "./pages/Home";
import DeckView from "./pages/DeckView";
import StudySession from "./pages/StudySession";
import "./App.css";

export default function App() {
  const [screen, setScreen] = useState("home");
  const [activeDeck, setActiveDeck] = useState(null);
  const [studyMode, setStudyMode] = useState("classic");

  function selectDeck(deck) {
    setActiveDeck(deck);
    setScreen("deck");
  }

  function startStudy(deck, mode) {
    setActiveDeck(deck);
    setStudyMode(mode);
    setScreen("study");
  }

  if (screen === "study") {
    return <StudySession deck={activeDeck} mode={studyMode} onBack={() => setScreen("deck")} />;
  }
  if (screen === "deck") {
    return <DeckView deck={activeDeck} onStudy={startStudy} onBack={() => setScreen("home")} />;
  }
  return <Home onSelectDeck={selectDeck} />;
}
