/**
 * Owner: Frontend (shared file — flag changes in group chat once other people
 * are also touching this during integration, per CONTRIBUTING.md)
 *
 * Top-level layout: connects the socket, holds detection/alert state, and
 * lays out VideoPanel + AlertsFeed + RoadmapCards.
 */
import { useEffect, useState } from "react";
import { connectSocket } from "./api/socket";
import VideoPanel from "./components/VideoPanel";
import AlertsFeed from "./components/AlertsFeed";
import RoadmapCard from "./components/RoadmapCard";

export default function App() {
  const [detections, setDetections] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const socket = connectSocket({
      onDetection: setDetections,
      onAlert: (alert) => setAlerts((prev) => [alert, ...prev]),
    });
    return () => socket.close();
  }, []);

  return (
    <div className="app">
      <h1>IBVAP — Live Monitoring</h1>
      <div className="main-grid">
        <VideoPanel detections={detections} />
        <AlertsFeed alerts={alerts} />
      </div>
      <div className="roadmap-row">
        <RoadmapCard title="ANPR" description="Automatic number-plate recognition — same pipeline, next module." />
        <RoadmapCard title="Face Recognition" description="Face detection and matching against watchlists." />
        <RoadmapCard title="Night Mode" description="Low-light enhanced detection for night-time movement." />
      </div>
    </div>
  );
}
