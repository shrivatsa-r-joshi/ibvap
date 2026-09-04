import React from 'react';
import RoadmapCard from './RoadmapCard';
import { ShieldAlertIcon, SparklesIcon, EyeIcon, CameraIcon, ActivityIcon } from './Icons';

export default function RoadmapSection() {
  const cards = [
    {
      title: "Virtual Perimeter Intrusion",
      badge: "Feature 2 · Active Beta",
      badgeType: "beta",
      icon: <ShieldAlertIcon size={20} />,
      pipeline: "Coordinate Geometry Engine",
      description: "Real-time tripwire and line-crossing detection with automated SMS and dashboard alerting.",
      readiness: 95,
      details: "Monitors object foot/wheel contact coordinates across the configured boundary vector (FENCE_LINE_COORDS). Already running in backend detection pipeline.",
    },
    {
      title: "ANPR / License Plate Recognition",
      badge: "Coming Soon",
      badgeType: "upcoming",
      icon: <CameraIcon size={20} />,
      pipeline: "Vehicle Crop + OCR",
      description: "Automated vehicle license plate extraction and database verification for cross-border transit checkpoints.",
      readiness: 65,
      details: "Crops bounding boxes flagged as 'vehicle' from YOLOv8, runs perspective rectification and lightweight CRNN OCR.",
    },
    {
      title: "Biometric Face Recognition",
      badge: "Coming Soon",
      badgeType: "upcoming",
      icon: <EyeIcon size={20} />,
      pipeline: "Face Alignment + Embeddings",
      description: "High-accuracy facial alignment and watchlist verification across CCTV video streams.",
      readiness: 50,
      details: "Extracts detected person crops, identifies facial landmarks, and computes cosine similarity against national security database vectors.",
    },
    {
      title: "Thermal & Night-Vision Analytics",
      badge: "Coming Soon",
      badgeType: "upcoming",
      icon: <SparklesIcon size={20} />,
      pipeline: "LWIR / FLIR Contrast Engine",
      description: "Adaptive histogram equalization and thermal signature enhancement for zero-lux night surveillance.",
      readiness: 45,
      details: "Pre-processes incoming low-light and infrared RTSP camera feeds with CLAHE and gamma curve adjustment prior to YOLOv8 inference.",
    },
    {
      title: "Suspicious Loitering & Behavior AI",
      badge: "Coming Soon",
      badgeType: "upcoming",
      icon: <ActivityIcon size={20} />,
      pipeline: "Trajectory & Dwell Time",
      description: "Behavioral analytics detecting prolonged stationary dwelling, perimeter pacing, and sudden evasive trajectories.",
      readiness: 40,
      details: "Analyzes persistent ByteTrack trajectory histories to calculate dwell velocity vectors and perimeter boundary proximity risk scores.",
    },
  ];

  return (
    <section className="apple-roadmap-section">
      <div className="section-header">
        <div>
          <span className="section-eyebrow">PLATFORM CAPABILITIES</span>
          <h2 className="section-heading">Surveillance Roadmap & Extended Capabilities</h2>
        </div>
        <p className="section-caption">
          AI Detection & Persistent Tracking are live. Additional modules leverage the shared YOLOv8 coordinate schema.
        </p>
      </div>

      <div className="apple-bento-grid">
        {cards.map((card, idx) => (
          <RoadmapCard key={idx} {...card} />
        ))}
      </div>
    </section>
  );
}
