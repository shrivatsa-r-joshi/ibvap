/**
 * Owner: Frontend
 *
 * Trinetra Cinema-grade Video Monitoring Panel.
 * Responsive, high-precision canvas overlay synchronized with YOLOv8
 * multi-object persistent tracking, interactive fence positioning,
 * and drag-and-drop video file upload.
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  PlayIcon,
  PauseIcon,
  RefreshIcon,
  MaximizeIcon,
  LayersIcon,
  UploadIcon,
  SlidersIcon,
} from './Icons';

export default function VideoPanel({
  detections,
  isPaused = false,
  onTogglePause,
  onRestart,
  overlays = { boxes: true, labels: true, fence: true },
  fenceCoords = [0.05, 0.52, 0.95, 0.52],
  onUpdateFenceCoords,
  videoFeedUrl = "/api/video/feed",
  onUploadFile,
  activeCamera = 'cam1',
  cameras = [],
  onSelectCamera,
  cameraName = 'CAM-01',
  cameraSector = 'Perimeter Fence Sector A',
}) {
  const containerRef = useRef(null);
  const viewportRef = useRef(null);
  const canvasRef = useRef(null);
  const imgRef = useRef(null);
  const fileInputRef = useRef(null);

  const [streamError, setStreamError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAdjustingFence, setIsAdjustingFence] = useState(false);
  const [fenceY, setFenceY] = useState(fenceCoords[1] || 0.52);

  // Sync internal fenceY state when props change
  useEffect(() => {
    if (fenceCoords && fenceCoords.length >= 4) {
      setFenceY(fenceCoords[1]);
    }
  }, [fenceCoords]);

  // Dynamic canvas resizing with ResizeObserver
  const updateCanvasSize = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const rect = img.getBoundingClientRect();
    const width = Math.round(rect.width);
    const height = Math.round(rect.height);

    if (width > 0 && height > 0 && (canvas.width !== width || canvas.height !== height)) {
      canvas.width = width;
      canvas.height = height;
    }
  }, []);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const observer = new ResizeObserver(() => {
      updateCanvasSize();
    });
    observer.observe(viewport);

    return () => observer.disconnect();
  }, [updateCanvasSize]);

  // Redraw canvas overlay whenever detections update or resize occurs
  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = img.getBoundingClientRect();
    const width = rect.width || canvas.width || 640;
    const height = rect.height || canvas.height || 480;

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    // Check if any object has breached/tampered with the fence
    const hasActiveBreach = detections?.objects?.some((o) => o.crossed_fence);

    // 1. Draw Virtual Perimeter Fence Line (if enabled)
    if (overlays.fence && fenceCoords && fenceCoords.length === 4) {
      const [fx1, , fx2] = fenceCoords;
      const x1 = fx1 * width;
      const y1 = fenceY * height;
      const x2 = fx2 * width;
      const y2 = fenceY * height;

      ctx.save();
      // Outer glow: Red hazard if breach detected, Amber if secure
      const glowColor = hasActiveBreach ? 'rgba(255, 69, 58, 0.65)' : 'rgba(255, 159, 10, 0.4)';
      const lineColor = hasActiveBreach ? '#FF453A' : '#FF9F0A';

      ctx.strokeStyle = glowColor;
      ctx.lineWidth = hasActiveBreach ? 10 : 6;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Sharp dashed center line
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = hasActiveBreach ? 3.5 : 2.5;
      ctx.setLineDash([10, 6]);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Fence tag pill
      const midX = (x1 + x2) / 2;
      const midY = y1;
      ctx.setLineDash([]);
      ctx.fillStyle = hasActiveBreach ? 'rgba(255, 69, 58, 0.95)' : 'rgba(255, 159, 10, 0.92)';
      ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
      ctx.shadowBlur = 10;

      const fenceLabel = hasActiveBreach
        ? "⚡ PERIMETER WIRE BREACH DETECTED"
        : "⚡ TRINETRA PERIMETER TRIPWIRE";
      ctx.font = 'bold 11px "Plus Jakarta Sans", -apple-system, sans-serif';
      const textWidth = ctx.measureText(fenceLabel).width;

      ctx.beginPath();
      ctx.roundRect(midX - textWidth / 2 - 10, midY - 11, textWidth + 20, 22, 11);
      ctx.fill();

      ctx.fillStyle = hasActiveBreach ? '#FFFFFF' : '#000000';
      ctx.shadowBlur = 0;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(fenceLabel, midX, midY);
      ctx.restore();
    }

    // 2. Draw YOLOv8 Tracked Bounding Boxes & Tags
    if (detections && detections.objects && detections.objects.length > 0) {
      detections.objects.forEach((obj) => {
        const [nx1, ny1, nx2, ny2] = obj.bbox;
        const x1 = nx1 * width;
        const y1 = ny1 * height;
        const x2 = nx2 * width;
        const y2 = ny2 * height;
        const boxW = Math.max(10, x2 - x1);
        const boxH = Math.max(10, y2 - y1);

        const isPerson = obj.class === "person";
        const isVehicle = obj.class === "vehicle";
        const hasBreached = obj.crossed_fence;

        // Color palette (Emerald for Person, Cyan for Vehicle, Purple for Objects, Red for Breach)
        let mainColor = isPerson ? '#30D158' : (isVehicle ? '#0A84FF' : '#BF5AF2');
        let bgTint = isPerson
          ? 'rgba(48, 209, 88, 0.08)'
          : (isVehicle ? 'rgba(10, 132, 255, 0.08)' : 'rgba(191, 90, 242, 0.08)');

        if (hasBreached) {
          mainColor = '#FF453A';
          bgTint = 'rgba(255, 69, 58, 0.22)';
        }

        ctx.save();

        if (overlays.boxes) {
          // Semi-transparent box fill
          ctx.fillStyle = bgTint;
          ctx.beginPath();
          ctx.roundRect(x1, y1, boxW, boxH, 6);
          ctx.fill();

          // Apple Camera-Style Minimal Corner Brackets
          ctx.strokeStyle = mainColor;
          ctx.lineWidth = 2.5;
          ctx.shadowColor = mainColor;
          ctx.shadowBlur = 8;

          const cornerLen = Math.min(boxW * 0.25, boxH * 0.25, 18);

          ctx.beginPath();
          // Top-Left Corner
          ctx.moveTo(x1, y1 + cornerLen);
          ctx.lineTo(x1, y1);
          ctx.lineTo(x1 + cornerLen, y1);

          // Top-Right Corner
          ctx.moveTo(x2 - cornerLen, y1);
          ctx.lineTo(x2, y1);
          ctx.lineTo(x2, y1 + cornerLen);

          // Bottom-Right Corner
          ctx.moveTo(x2, y2 - cornerLen);
          ctx.lineTo(x2, y2);
          ctx.lineTo(x2 - cornerLen, y2);

          // Bottom-Left Corner
          ctx.moveTo(x1 + cornerLen, y2);
          ctx.lineTo(x1, y2);
          ctx.lineTo(x1, y2 - cornerLen);
          ctx.stroke();

          // Faint connecting outline
          ctx.strokeStyle = mainColor;
          ctx.globalAlpha = 0.25;
          ctx.lineWidth = 1;
          ctx.shadowBlur = 0;
          ctx.beginPath();
          ctx.roundRect(x1, y1, boxW, boxH, 6);
          ctx.stroke();
          ctx.globalAlpha = 1.0;
        }

        // Floating Tag Pill (ID, Class, Confidence)
        if (overlays.labels) {
          ctx.shadowBlur = 6;
          ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';

          const tagText = `${obj.id} · ${obj.class.toUpperCase()} ${Math.round(obj.confidence * 100)}%`;
          ctx.font = '600 11px "Plus Jakarta Sans", -apple-system, sans-serif';
          const tagMetrics = ctx.measureText(tagText);
          const tagW = tagMetrics.width + 18;
          const tagH = 20;
          const tagX = Math.max(4, Math.min(x1, width - tagW - 4));
          const tagY = Math.max(tagH + 4, y1 - 6);

          // Frosted pill container
          ctx.fillStyle = 'rgba(18, 20, 30, 0.88)';
          ctx.beginPath();
          ctx.roundRect(tagX, tagY - tagH, tagW, tagH, 6);
          ctx.fill();

          // Border on pill
          ctx.strokeStyle = mainColor;
          ctx.lineWidth = 1;
          ctx.stroke();

          // Status dot in pill
          ctx.fillStyle = mainColor;
          ctx.beginPath();
          ctx.arc(tagX + 8, tagY - tagH / 2, 3, 0, 2 * Math.PI);
          ctx.fill();

          // Text label
          ctx.fillStyle = '#FFFFFF';
          ctx.shadowBlur = 0;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(tagText, tagX + 16, tagY - tagH / 2 + 1);
        }

        ctx.restore();
      });
    }
  }, [detections, overlays, fenceCoords, fenceY]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch((err) => console.log(err));
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      onUploadFile?.(file);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      onUploadFile?.(file);
    }
  };

  const handleFenceYSlider = (newY) => {
    setFenceY(newY);
    onUpdateFenceCoords?.([fenceCoords[0] || 0.1, newY, fenceCoords[2] || 0.9, newY]);
  };

  const objectCount = detections?.objects?.length || 0;
  const frameId = detections?.frame_id || 0;
  const timestamp = detections?.timestamp
    ? new Date(detections.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();

  return (
    <div
      className={`apple-video-card ${isFullscreen ? 'fullscreen' : ''} ${isDragOver ? 'drag-active' : ''}`}
      ref={containerRef}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden File Input for Video Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="video/mp4,video/x-m4v,video/*"
        style={{ display: 'none' }}
      />

      {/* CCTV Multi-Camera Matrix Channel Bar */}
      <div className="camera-channel-bar">
        <div className="channel-bar-label">
          <span className="live-pulse-dot" />
          <span>CCTV FEEDS</span>
        </div>
        <div className="channel-pills">
          {cameras && cameras.length > 0 ? (
            cameras.map((cam) => {
              const isActive = activeCamera === cam.id;
              return (
                <button
                  key={cam.id}
                  type="button"
                  className={`camera-channel-pill ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectCamera?.(cam.id)}
                  title={`${cam.name}: ${cam.sector} (${cam.type})`}
                >
                  <span className={`cam-indicator ${isActive ? 'active' : ''}`} />
                  <span className="cam-name">{cam.name}</span>
                  <span className="cam-sector">{cam.sector}</span>
                </button>
              );
            })
          ) : (
            <span className="no-cameras-hint">Detecting sensor nodes...</span>
          )}
          <button
            type="button"
            className="camera-channel-pill upload-pill"
            onClick={() => fileInputRef.current?.click()}
            title="Upload any video clip to inspect and track"
          >
            <UploadIcon size={12} />
            <span>+ Add Feed</span>
          </button>
        </div>
      </div>

      {/* Video Viewport Area */}
      <div className="video-viewport" ref={viewportRef}>
        {/* Live Video Stream from Backend */}
        <img
          ref={imgRef}
          src={videoFeedUrl}
          alt="Trinetra Live CCTV Stream"
          className="live-video-stream"
          onError={() => setStreamError(true)}
          onLoad={() => {
            setStreamError(false);
            updateCanvasSize();
          }}
        />

        {/* High-Precision Real-Time Canvas Overlay */}
        <canvas ref={canvasRef} className="tracking-canvas-overlay" />

        {/* Drag & Drop Overlay */}
        {isDragOver && (
          <div className="drag-drop-curtain">
            <UploadIcon size={44} className="drag-icon" />
            <h3>Drop Video to Inspect with YOLOv8</h3>
            <p>Release to upload and start tracking immediately</p>
          </div>
        )}

        {/* Video HUD Top Elements */}
        <div className="hud-top">
          <div className="hud-badge live-badge">
            <span className="rec-dot" />
            <span>TRINETRA LIVE</span>
            <span className="hud-separator">|</span>
            <span className="camera-id">{cameraName} · {cameraSector}</span>
          </div>

          <div className="hud-badge telemetry-badge">
            <span className="frame-counter">FRAME #{frameId}</span>
            <span className="hud-separator">|</span>
            <span className="hud-time">{timestamp}</span>
            <span className="hud-separator">|</span>
            <span className={`target-count ${objectCount > 0 ? 'active' : ''}`}>
              {objectCount} {objectCount === 1 ? 'TARGET' : 'TARGETS'}
            </span>
          </div>
        </div>

        {/* Interactive Fence Adjustment Bar */}
        {isAdjustingFence && (
          <div className="fence-slider-bar">
            <span>Perimeter Height: {Math.round(fenceY * 100)}%</span>
            <input
              type="range"
              min="0.10"
              max="0.90"
              step="0.02"
              value={fenceY}
              onChange={(e) => handleFenceYSlider(parseFloat(e.target.value))}
              className="apple-slider"
            />
            <button
              type="button"
              className="close-fence-btn"
              onClick={() => setIsAdjustingFence(false)}
            >
              Done
            </button>
          </div>
        )}

        {/* Stream Error Fallback */}
        {streamError && (
          <div className="stream-error-overlay">
            <div className="error-card">
              <LayersIcon size={32} className="error-icon" />
              <h4>Video Stream Offline</h4>
              <p>Connecting to backend video feed at <code>{videoFeedUrl}</code>...</p>
              <button
                type="button"
                className="retry-btn"
                onClick={() => {
                  setStreamError(false);
                  if (imgRef.current) imgRef.current.src = `${videoFeedUrl}?t=${Date.now()}`;
                }}
              >
                <RefreshIcon size={14} /> Retry Feed
              </button>
            </div>
          </div>
        )}

        {/* Bottom Floating Control Dock */}
        <div className="hud-bottom">
          <div className="control-dock">
            <button
              type="button"
              className={`dock-btn ${isPaused ? 'paused' : ''}`}
              onClick={onTogglePause}
              title={isPaused ? "Resume Stream" : "Pause Stream"}
            >
              {isPaused ? <PlayIcon size={14} /> : <PauseIcon size={14} />}
              <span>{isPaused ? 'Resume' : 'Pause'}</span>
            </button>

            <button
              type="button"
              className="dock-btn"
              onClick={onRestart}
              title="Reset Persistent Tracking IDs"
            >
              <RefreshIcon size={13} />
              <span>Reset</span>
            </button>

            <button
              type="button"
              className="dock-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Upload any video file to track"
            >
              <UploadIcon size={13} />
              <span>Upload Clip</span>
            </button>

            <button
              type="button"
              className={`dock-btn ${isAdjustingFence ? 'active' : ''}`}
              onClick={() => setIsAdjustingFence(!isAdjustingFence)}
              title="Adjust Virtual Fence Line Height"
            >
              <SlidersIcon size={13} />
              <span>Fence</span>
            </button>

            <div className="dock-divider" />

            <button
              type="button"
              className="dock-icon-btn"
              onClick={toggleFullscreen}
              title="Toggle Fullscreen"
            >
              <MaximizeIcon size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
