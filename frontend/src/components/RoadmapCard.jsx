/**
 * Owner: Frontend
 *
 * Apple-inspired Bento Grid card for roadmap / upcoming features.
 * Features:
 *   - Apple visionOS glassmorphism card
 *   - Specular highlight hover border
 *   - Status pills (Coming Soon, Active Beta, In Development)
 *   - Interactive modal inspection
 */

import React, { useState } from 'react';
import { SparklesIcon, ChevronRightIcon, CloseIcon, CpuIcon } from './Icons';

export default function RoadmapCard({
  title,
  description,
  badge = "Coming Soon",
  badgeType = "upcoming", // "beta" | "upcoming" | "planned"
  icon,
  pipeline = "YOLOv8 Core Pipeline",
  readiness = 80,
  details = "",
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div
        className={`apple-bento-card ${badgeType}`}
        onClick={() => setIsOpen(true)}
        role="button"
        tabIndex={0}
      >
        <div className="card-ambient-glow" />

        <div className="bento-card-header">
          <div className="bento-icon-box">
            {icon || <SparklesIcon size={18} />}
          </div>

          <span className={`bento-badge ${badgeType}`}>
            {badge}
          </span>
        </div>

        <div className="bento-card-body">
          <h3 className="bento-title">{title}</h3>
          <p className="bento-desc">{description}</p>
        </div>

        <div className="bento-card-footer">
          <span className="pipeline-tag">{pipeline}</span>
          <div className="learn-more">
            <span>Details</span>
            <ChevronRightIcon size={14} />
          </div>
        </div>
      </div>

      {/* Apple-styled Sheet Modal */}
      {isOpen && (
        <div className="apple-modal-backdrop" onClick={() => setIsOpen(false)}>
          <div className="apple-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <div className="modal-icon">{icon || <SparklesIcon size={20} />}</div>
                <div>
                  <h2 className="modal-title">{title}</h2>
                  <span className={`bento-badge ${badgeType}`}>{badge}</span>
                </div>
              </div>

              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsOpen(false)}
              >
                <CloseIcon size={16} />
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-desc">{description}</p>

              <div className="modal-section">
                <h4>Pipeline Architecture</h4>
                <div className="pipeline-card">
                  <CpuIcon size={16} className="pipe-icon" />
                  <div>
                    <strong>Shared YOLOv8 + Tracker Backbone</strong>
                    <p>Integrates downstream of <code>detection/detector.py</code>. Consumes normalized tracking coordinates without requiring secondary ML models.</p>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h4>Technical Scope</h4>
                <p>{details || "Designed as part of the IBVAP 8-capability surveillance specification. Fully architected to deploy alongside real-time CCTV feeds."}</p>
              </div>

              <div className="readiness-meter">
                <div className="meter-label">
                  <span>Architecture Completeness</span>
                  <span>{readiness}%</span>
                </div>
                <div className="meter-track">
                  <div className="meter-fill" style={{ width: `${readiness}%` }} />
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-action-btn secondary"
                onClick={() => setIsOpen(false)}
              >
                Dismiss
              </button>
              <button
                type="button"
                className="modal-action-btn primary"
                onClick={() => setIsOpen(false)}
              >
                Acknowledge Roadmap
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
