import React from 'react';
import {
  TrinetraLogo,
  ActivityIcon,
  CpuIcon,
  SlidersIcon,
  SunIcon,
  MoonIcon,
  UploadIcon,
  FilterIcon,
} from './Icons';

export default function Header({
  status,
  fps = 0,
  connectionState = 'connected',
  confThreshold = 0.28,
  onConfChange,
  overlays = { boxes: true, labels: true, fence: true },
  onToggleOverlay,
  theme = 'light',
  onToggleTheme,
  onUploadClick,
  detectAll = false,
  onToggleDetectAll,
}) {
  const isOnline = connectionState === 'connected';

  return (
    <header className="apple-header">
      {/* Brand Identity */}
      <div className="header-left">
        <div className="brand-badge">
          <div className="trinetra-emblem-wrap" title="Trinetra: Three-Eye Surveillance Intelligence">
            <TrinetraLogo size={34} className="trinetra-logo-svg" />
          </div>
          <div className="brand-text">
            <div className="brand-title">
              <span>TRINETRA</span>
              <span className="brand-pill">SIH 26187</span>
            </div>
            <p className="brand-subtitle">INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM</p>
          </div>
        </div>
      </div>

      {/* Center Live Telemetry Cluster */}
      <div className="header-center">
        <div className="telemetry-cluster">
          <div className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
            <span className="pulsing-dot" />
            <span className="status-label">{isOnline ? 'SENSOR ONLINE' : 'CONNECTING...'}</span>
          </div>

          <div className="metric-pill" title="Real-time Inference & Persistent Tracking FPS">
            <ActivityIcon size={12} className="metric-icon" />
            <span className="metric-value">{fps > 0 ? fps.toFixed(1) : '--.-'}</span>
            <span className="metric-unit">FPS</span>
          </div>

          <div className="metric-pill device-pill" title="Hardware Neural Acceleration Engine">
            <CpuIcon size={12} className="metric-icon" />
            <span className="metric-value">{status?.device ? status.device.toUpperCase() : 'MPS ACCEL'}</span>
          </div>
        </div>
      </div>

      {/* Right Controls & Actions */}
      <div className="header-right">
        {/* Quick Upload Video Feed Button */}
        <button
          type="button"
          className="header-action-btn upload-btn"
          onClick={onUploadClick}
          title="Upload ANY video file (MP4, MOV, AVI) to analyze"
        >
          <UploadIcon size={14} />
          <span>Upload Feed</span>
        </button>

        {/* Target Filter Toggle (Security vs All 80 Objects) */}
        <button
          type="button"
          className={`toggle-chip filter-chip ${detectAll ? 'active' : ''}`}
          onClick={onToggleDetectAll}
          title="Toggle People & Vehicles vs All 80 COCO Objects"
        >
          <FilterIcon size={12} />
          <span>{detectAll ? 'All Objects' : 'People & Vehicles'}</span>
        </button>

        {/* Confidence Threshold Slider */}
        <div className="slider-control" title="Adjust AI detection confidence threshold">
          <SlidersIcon size={12} className="control-icon" />
          <span className="slider-label">Conf</span>
          <input
            type="range"
            min="0.10"
            max="0.80"
            step="0.02"
            value={confThreshold}
            onChange={(e) => onConfChange(parseFloat(e.target.value))}
            className="apple-slider"
          />
          <span className="slider-badge">{Math.round(confThreshold * 100)}%</span>
        </div>

        {/* Overlay Feature Toggles */}
        <div className="segmented-control overlay-segmented">
          <button
            type="button"
            className={`segment-btn ${overlays.boxes ? 'active' : ''}`}
            onClick={() => onToggleOverlay('boxes')}
            title="Toggle Bounding Boxes"
          >
            Boxes
          </button>
          <button
            type="button"
            className={`segment-btn ${overlays.labels ? 'active' : ''}`}
            onClick={() => onToggleOverlay('labels')}
            title="Toggle ID & Confidence Tags"
          >
            Labels
          </button>
          <button
            type="button"
            className={`segment-btn ${overlays.fence ? 'active' : ''}`}
            onClick={() => onToggleOverlay('fence')}
            title="Toggle Virtual Perimeter Tripwire"
          >
            Tripwire
          </button>
        </div>

        {/* Theme Switcher Segmented Control (Light / Dark) */}
        <div className="segmented-control theme-switcher" title="Toggle Light / Dark Appearance">
          <button
            type="button"
            className={`segment-btn ${theme === 'light' ? 'active' : ''}`}
            onClick={() => onToggleTheme('light')}
          >
            <SunIcon size={13} />
            <span>Light</span>
          </button>
          <button
            type="button"
            className={`segment-btn ${theme === 'dark' ? 'active' : ''}`}
            onClick={() => onToggleTheme('dark')}
          >
            <MoonIcon size={13} />
            <span>Dark</span>
          </button>
        </div>
      </div>
    </header>
  );
}
