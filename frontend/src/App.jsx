/**
 * Owner: Frontend
 *
 * Master Dashboard Application with Apple Human Interface Design aesthetics.
 * Connects WebSocket real-time telemetry, orchestrates VideoPanel,
 * LiveTrackingFeed, and RoadmapSection.
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { connectSocket } from './api/socket';
import Header from './components/Header';
import VideoPanel from './components/VideoPanel';
import LiveTrackingFeed from './components/LiveTrackingFeed';
import RoadmapSection from './components/RoadmapSection';
import AlertNotificationPopup from './components/AlertNotificationPopup';
import './styles/App.css';

export default function App() {
  const [detections, setDetections] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState(null);
  const [connectionState, setConnectionState] = useState('connecting');
  const [source, setSource] = useState('sample');
  const [cameras, setCameras] = useState([]);
  const [activeCamera, setActiveCamera] = useState('cam1');
  const [activeAlertPopup, setActiveAlertPopup] = useState(null);
  const [fenceCoords, setFenceCoords] = useState([0.05, 0.52, 0.95, 0.52]);
  const [isPaused, setIsPaused] = useState(false);
  const [confThreshold, setConfThreshold] = useState(0.45);
  const [detectAll, setDetectAll] = useState(false);
  const [uploadNotification, setUploadNotification] = useState(null);
  const [overlays, setOverlays] = useState({
    boxes: true,
    labels: true,
    fence: true,
  });
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('ibvap_theme') || 'light';
  });

  const fileInputRef = useRef(null);

  const handleToggleTheme = (newTheme) => {
    setTheme(newTheme);
    localStorage.setItem('ibvap_theme', newTheme);
  };

  // Fetch camera feeds list and active camera
  const fetchCameras = useCallback(async () => {
    try {
      const res = await fetch('/api/cameras');
      if (res.ok) {
        const data = await res.json();
        if (data.cameras && Array.isArray(data.cameras)) {
          setCameras(data.cameras);
        }
        if (data.active_camera) {
          setActiveCamera(data.active_camera);
        }
      }
    } catch (e) {
      // Backend may be booting up
    }
  }, []);

  // Fetch backend telemetry status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        if (data.source) setSource(data.source);
        if (data.is_paused !== undefined) setIsPaused(data.is_paused);
        if (data.confidence_threshold) setConfThreshold(data.confidence_threshold);
        if (data.fence_coords && Array.isArray(data.fence_coords) && data.fence_coords.length === 4) {
          setFenceCoords((prev) => {
            if (!prev || Math.abs(prev[1] - data.fence_coords[1]) > 0.005) {
              return data.fence_coords;
            }
            return prev;
          });
        }
      }
    } catch (e) {
      // Backend may be booting up
    }
  }, []);

  // Fetch existing recorded alerts from SQLite DB
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/events?type=alert&limit=50');
      if (res.ok) {
        const data = await res.json();
        if (data.events && Array.isArray(data.events)) {
          setAlerts(data.events);
        }
      }
    } catch (e) {
      console.error("Failed to load stored alerts:", e);
    }
  }, []);

  // Connect WebSocket stream & bootstrap data
  useEffect(() => {
    fetchStatus();
    fetchAlerts();
    fetchCameras();
    const statusInterval = setInterval(() => {
      fetchStatus();
      fetchCameras();
    }, 3000);

    const socket = connectSocket({
      onDetection: (msg) => {
        setDetections(msg);
      },
      onAlert: (alert) => {
        setAlerts((prev) => [alert, ...prev.slice(0, 49)]); // Keep latest 50
        setActiveAlertPopup(alert);
      },
      onStatusChange: (st) => {
        setConnectionState(st);
      },
    });

    return () => {
      clearInterval(statusInterval);
      socket.close();
    };
  }, [fetchStatus, fetchAlerts, fetchCameras]);

  // Handle camera channel selection (CAM-01, CAM-02, CAM-03, CAM-04, etc.)
  const handleSelectCamera = async (camId) => {
    setActiveCamera(camId);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: camId }),
      });
      fetchCameras();
      fetchStatus();
    } catch (err) {
      console.error("Failed to switch camera:", err);
    }
  };

  // Handle stream source change (Demo Clip vs Webcam vs Patrol Clip)
  const handleSourceChange = async (newSource) => {
    setSource(newSource);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: newSource }),
      });
      fetchStatus();
      fetchCameras();
    } catch (err) {
      console.error("Failed to switch source:", err);
    }
  };

  // Handle file upload (any video: MP4, MOV, AVI, etc.)
  const handleUploadFile = async (file) => {
    if (!file) return;
    try {
      setUploadNotification(`Uploading ${file.name}...`);
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadNotification(`Tracking active on ${file.name}`);
        setTimeout(() => setUploadNotification(null), 4000);
        setSource(data.filename || file.name);
        fetchStatus();
      } else {
        const err = await res.json();
        alert(`Upload error: ${err.error || 'Failed to upload video'}`);
        setUploadNotification(null);
      }
    } catch (err) {
      console.error("Failed to upload video:", err);
      setUploadNotification(null);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleUploadFile(e.target.files[0]);
    }
  };

  // Handle detection mode toggle (Security Targets vs All 80 COCO Objects)
  const handleToggleDetectAll = async () => {
    const nextVal = !detectAll;
    setDetectAll(nextVal);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detect_all: nextVal }),
      });
    } catch (err) {
      console.error("Failed to toggle detect_all:", err);
    }
  };

  // Handle confidence slider adjustment
  const handleConfChange = async (newConf) => {
    setConfThreshold(newConf);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confidence: newConf }),
      });
    } catch (err) {
      console.error("Failed to update confidence:", err);
    }
  };

  // Handle stream pause / resume
  const handleTogglePause = async () => {
    const nextPaused = !isPaused;
    setIsPaused(nextPaused);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: nextPaused ? 'pause' : 'resume' }),
      });
    } catch (err) {
      console.error("Failed to toggle pause:", err);
    }
  };

  // Handle tracker reset
  const handleRestart = async () => {
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'restart' }),
      });
      setAlerts([]);
    } catch (err) {
      console.error("Failed to restart:", err);
    }
  };

  // Handle virtual fence coordinate adjustment from slider
  const handleUpdateFenceCoords = useCallback(async (newCoords) => {
    setFenceCoords(newCoords);
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fence_coords: newCoords }),
      });
    } catch (err) {
      console.error("Failed to update fence coords:", err);
    }
  }, []);

  // Trigger simulated intrusion alert
  const handleSimulateAlert = async () => {
    try {
      const res = await fetch('/api/alerts/simulate', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.alert) {
          setAlerts((prev) => [data.alert, ...prev.slice(0, 49)]);
          setActiveAlertPopup(data.alert);
        }
      }
    } catch (err) {
      console.error("Failed to simulate alert:", err);
    }
  };

  // Clear alert log display
  const handleClearAlerts = () => {
    setAlerts([]);
  };

  // Handle overlay toggles (boxes, labels, fence)
  const handleToggleOverlay = (key) => {
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const currentFps = status?.fps || (detections ? 30.0 : 0.0);
  const currentCamObj = cameras.find((c) => c.id === activeCamera) || {
    name: 'CAM-01',
    sector: 'Perimeter Wire Sector A',
  };

  return (
    <div className={`apple-dashboard-root theme-${theme}`}>
      <div className="background-mesh-glow" />

      {/* Floating Apple-styled Real-time Alert Notification Banner */}
      <AlertNotificationPopup
        alert={activeAlertPopup}
        onDismiss={() => setActiveAlertPopup(null)}
      />

      {/* Hidden File Input for Video Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept="video/mp4,video/x-m4v,video/quicktime,video/x-matroska,video/*"
        style={{ display: 'none' }}
      />

      {/* Floating Upload Notification Toast */}
      {uploadNotification && (
        <div className="upload-toast-notification">
          <span className="toast-dot" />
          <span>{uploadNotification}</span>
        </div>
      )}

      {/* Apple-styled Frosted Header Bar */}
      <Header
        status={status}
        fps={currentFps}
        connectionState={connectionState}
        source={source}
        onSourceChange={handleSourceChange}
        confThreshold={confThreshold}
        onConfChange={handleConfChange}
        overlays={overlays}
        onToggleOverlay={handleToggleOverlay}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        onUploadClick={() => fileInputRef.current?.click()}
        detectAll={detectAll}
        onToggleDetectAll={handleToggleDetectAll}
      />

      <main className="dashboard-main-container">
        {/* Top Hero Layout: 2-Column Cinema Monitor & Live Targets Feed */}
        <div className="surveillance-hero-grid">
          <div className="video-column">
            <VideoPanel
              detections={detections}
              isPaused={isPaused}
              onTogglePause={handleTogglePause}
              onRestart={handleRestart}
              overlays={overlays}
              fenceCoords={fenceCoords}
              onUpdateFenceCoords={handleUpdateFenceCoords}
              onUploadFile={handleUploadFile}
              activeCamera={activeCamera}
              cameras={cameras}
              onSelectCamera={handleSelectCamera}
              cameraName={currentCamObj.name}
              cameraSector={currentCamObj.sector}
            />
          </div>

          <div className="sidebar-column">
            <LiveTrackingFeed
              detections={detections}
              alerts={alerts}
              onSimulateAlert={handleSimulateAlert}
              onClearAlerts={handleClearAlerts}
            />
          </div>
        </div>

        {/* Bottom Section: Apple Bento Grid with Coming Soon / Roadmap Capabilities */}
        <RoadmapSection />
      </main>

      {/* Apple-styled Minimalist Footer */}
      <footer className="apple-footer">
        <div className="footer-content">
          <span>TRINETRA · Three-Eye Border Surveillance Intelligence · SIH 26187</span>
          <span className="footer-sep">•</span>
          <span>Ultralytics YOLOv8 Persistent Multi-Object Tracking Engine</span>
          <span className="footer-sep">•</span>
          <span className="footer-status">SYSTEM OPERATIONAL</span>
        </div>
      </footer>
    </div>
  );
}
