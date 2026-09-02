/**
 * Owner: Frontend
 *
 * Static, clearly-labelled cards for the features NOT live in this demo
 * (ANPR, face recognition, night-mode) so the dashboard reads as a complete
 * platform even though only detection + fence-alert are wired up live.
 *
 * Props:
 *   title: string
 *   description: string
 */
export default function RoadmapCard({ title, description }) {
  return (
    <div className="roadmap-card">
      <span className="roadmap-badge">Roadmap</span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
