import ChatPanel from "../components/ChatPanel";
import MapPanel from "../components/MapPanel";

export default function Home() {
  return (
    <main className="app-shell">
      <MapPanel />
      <ChatPanel />
    </main>
  );
}
