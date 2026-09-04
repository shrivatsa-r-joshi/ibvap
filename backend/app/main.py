"""
Owner: Backend (Trinetra SIH 26187)

FastAPI entrypoint and core system orchestrator for Trinetra.
Responsibilities:
  1. Expose the `/ws/live` WebSocket endpoint for real-time detection & alert broadcasts.
  2. Run the continuous video analytics loop:
     frame -> detector.get_detections() -> fence.check_fence_crossings() -> ws.broadcast + db + alerts.
  3. Expose REST endpoints:
     - GET /api/video/feed (MJPEG live stream)
     - GET /api/status (System telemetry & health)
     - GET /api/events (Detection & alert logs)
     - POST /api/control (Source switching, playback control, confidence, fence adjustment)
     - POST /api/upload (Upload ANY video file for instant tracking)
     - POST /api/alerts/simulate (Simulate intrusion breach for live demonstration)
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app import config
from app.alerts import notifier
from app.db import models
from app.detection import detector, fence
from app.ws.manager import ConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("trinetra.main")

app = FastAPI(
    title="Trinetra — Intelligent Border Video Analytics Platform",
    description="Three-Eye Border Surveillance Platform with YOLOv8 object detection, persistent tracking, and intrusion alerting.",
    version="2.0.0",
)

# Enable CORS for frontend Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

# Global state for video stream and background loop
_video_task: Optional[asyncio.Task] = None
_latest_jpeg_frame: Optional[bytes] = None
_is_running = True
_is_paused = False
_source_changed = False
_active_camera_id = "cam1"
_current_source = config.CAMERA_FEEDS["cam1"]["source"]
_frame_counter = 0


class ControlRequest(BaseModel):
    action: Optional[str] = None  # "pause", "resume", "restart", "switch_source"
    source: Optional[str] = None  # "sample", "webcam", or file/rtsp path
    camera_id: Optional[str] = None  # "cam1", "cam2", "cam3", "cam4", or "upload"
    confidence: Optional[float] = None
    fence_coords: Optional[List[float]] = None
    detect_all: Optional[bool] = None  # True for all 80 COCO classes, False for people & vehicles


async def video_processing_worker():
    """
    Background worker that continuously reads frames, performs YOLOv8 detection
    and persistent tracking, runs fence checks, and broadcasts results.
    """
    global _latest_jpeg_frame, _frame_counter, _current_source, _is_running, _is_paused, _source_changed

    logger.info("Starting Trinetra video processing background worker...")

    while _is_running:
        # Determine source path
        if _current_source == "webcam":
            cap_source = 0
        elif _current_source == "rtsp" and config.RTSP_URL:
            cap_source = config.RTSP_URL
        else:
            cap_source = config.resolve_video_path(str(_current_source))

        logger.info("Opening video capture source: %s", cap_source)
        try:
            cap = detector.open_video_source(cap_source)
        except Exception as e:
            logger.error("Failed to open video source '%s': %s. Retrying in 3s...", cap_source, e)
            await asyncio.sleep(3.0)
            continue

        fence.reset_fence_tracker()
        detector_instance = detector.get_detector()
        detector_instance.reset_tracker()

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = 1.0 / max(10.0, min(video_fps, 60.0))

        while _is_running and cap.isOpened():
            if _source_changed:
                logger.info("Video source changed to %s. Reloading capture.", _current_source)
                _source_changed = False
                break

            if _is_paused:
                await asyncio.sleep(0.1)
                continue

            t_start = time.perf_counter()
            ret, frame = cap.read()

            if not ret or frame is None:
                if _source_changed:
                    _source_changed = False
                    break
                # If sample video reached the end, loop it smoothly
                if _current_source != "webcam":
                    logger.info("Video ended; looping playback.")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    detector_instance.reset_tracker()
                    fence.reset_fence_tracker()
                    continue
                else:
                    logger.warning("Webcam stream disconnected or ended.")
                    break

            _frame_counter += 1

            # 1. Update latest compressed JPEG frame for MJPEG streaming
            ret_enc, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
            if ret_enc:
                _latest_jpeg_frame = buffer.tobytes()

            # 2. AI Layer: YOLOv8 Detection & Persistent Tracking
            detection_message = detector_instance.get_detections(frame, _frame_counter)

            # 3. AI Secondary Layer: Virtual Fence Intrusion & Wire Tampering Check
            cam_info = config.CAMERA_FEEDS.get(_active_camera_id, {})
            cam_name = cam_info.get("name", "CAM-01")
            cam_sector = cam_info.get("sector", "Perimeter Sector A")
            alerts = fence.check_fence_crossings(
                detection_message["objects"],
                location=f"{cam_name} · {cam_sector}",
            )

            # 4. Broadcast Detection Message over WebSocket
            await manager.broadcast(detection_message)

            # 5. Handle Alerts: WebSocket + SMS/Email dispatch + DB logging
            for alert in alerts:
                await manager.broadcast(alert)
                notifier.send_alert(alert)
                models.log_event(alert)

            # 6. Log detection message to DB if it contains objects
            if detection_message["objects"]:
                models.log_event(detection_message)

            # Regulate processing rate to match camera/video stream
            elapsed = time.perf_counter() - t_start
            sleep_time = max(0.001, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

        cap.release()
        logger.info("Video capture released.")
        await asyncio.sleep(1.0)


@app.on_event("startup")
async def startup():
    global _video_task
    models.init_db()
    _video_task = asyncio.create_task(video_processing_worker())


@app.on_event("shutdown")
async def shutdown():
    global _is_running, _video_task
    _is_running = False
    if _video_task:
        _video_task.cancel()


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint consumed by frontend (socket.js).
    Receives detection messages and alert events in real time.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep-alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/api/status")
async def get_status():
    """Returns real-time backend telemetry, FPS, and tracking metrics."""
    detector_inst = detector.get_detector()
    active_fence = fence.get_fence_coords()
    cam_info = config.CAMERA_FEEDS.get(_active_camera_id, {})
    return {
        "status": "online",
        "fps": detector_inst.current_fps,
        "total_frames": _frame_counter,
        "source": _current_source,
        "active_camera_id": _active_camera_id,
        "camera_name": cam_info.get("name", "CAM-01"),
        "camera_sector": cam_info.get("sector", "Perimeter Sector A"),
        "is_paused": _is_paused,
        "active_clients": len(manager.active_connections),
        "model": detector_inst.model_path,
        "confidence_threshold": detector_inst.conf_threshold,
        "fence_coords": list(active_fence),
        "device": detector_inst.device,
    }


@app.get("/api/cameras")
async def list_cameras():
    """Returns available CCTV camera channels and their sector descriptions."""
    feeds = []
    for cid, feed in config.CAMERA_FEEDS.items():
        feeds.append({
            "id": cid,
            "name": feed["name"],
            "sector": feed["sector"],
            "is_active": (cid == _active_camera_id),
            "source_type": "webcam" if feed["source"] == "webcam" else "video",
        })
    return {"cameras": feeds, "active_camera": _active_camera_id}


@app.get("/api/events")
async def get_events(limit: int = 50, type: Optional[str] = None):
    """Returns recent detections and alerts stored in SQLite with unpacked payload."""
    raw_events = models.get_recent_events(limit=limit, event_type=type)
    events = []
    for ev in raw_events:
        item = dict(ev.get("payload") or {})
        item.setdefault("id", ev.get("id"))
        item.setdefault("type", ev.get("type"))
        item.setdefault("timestamp", ev.get("timestamp"))
        item.setdefault("object_id", ev.get("object_id"))
        item.setdefault("class", ev.get("class"))
        events.append(item)
    return {"events": events, "count": len(events)}


@app.post("/api/control")
async def control_stream(req: ControlRequest):
    """Control video stream playback, settings, and fence position."""
    global _is_paused, _current_source, _source_changed, _active_camera_id

    detector_inst = detector.get_detector()

    if req.action == "pause":
        _is_paused = True
    elif req.action == "resume":
        _is_paused = False
    elif req.action == "restart":
        _is_paused = False
        detector_inst.reset_tracker()
        fence.reset_fence_tracker()

    if req.camera_id:
        cid = req.camera_id
        if cid in config.CAMERA_FEEDS:
            feed = config.CAMERA_FEEDS[cid]
            _current_source = feed["source"]
            _active_camera_id = cid
            fence.set_fence_coords(feed["fence_coords"])
            _is_paused = False
            _source_changed = True
            detector_inst.reset_tracker()
            fence.reset_fence_tracker()
            logger.info("Camera switched to %s (%s)", cid, feed["name"])

    if req.source:
        if req.source == "sample" or req.source == "fence":
            _current_source = config.SAMPLE_VIDEO_PATH
        elif req.source == "patrol":
            _current_source = str(config.resolve_video_path("backend/sample_videos/getty_border_patrol.mp4"))
        else:
            _current_source = req.source
        _is_paused = False
        _source_changed = True
        detector_inst.reset_tracker()
        fence.reset_fence_tracker()

    if req.confidence is not None and 0.0 <= req.confidence <= 1.0:
        detector_inst.conf_threshold = req.confidence

    if req.fence_coords is not None and len(req.fence_coords) == 4:
        fence.set_fence_coords(tuple(req.fence_coords))

    if req.detect_all is not None:
        if req.detect_all:
            detector_inst.target_classes = None  # All 80 classes
            logger.info("YOLOv8 configured to detect all object classes.")
        else:
            detector_inst.target_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # People & Vehicles
            logger.info("YOLOv8 configured to detect people & vehicles.")

    cam_info = config.CAMERA_FEEDS.get(_active_camera_id, {})
    return {
        "status": "updated",
        "is_paused": _is_paused,
        "source": _current_source,
        "active_camera_id": _active_camera_id,
        "camera_name": cam_info.get("name", "CAM-01"),
        "camera_sector": cam_info.get("sector", "Perimeter Sector A"),
        "confidence_threshold": detector_inst.conf_threshold,
        "fence_coords": list(fence.get_fence_coords()),
    }


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Accepts ANY video file uploaded from frontend, stores it in sample_videos,
    switches active surveillance stream to this video, and starts YOLOv8 tracking!
    """
    global _current_source, _is_paused, _source_changed, _active_camera_id

    allowed_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_exts:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported format '{file_ext}'. Please upload an MP4, AVI, MOV, or MKV video."},
        )

    # Save destination in sample_videos
    backend_dir = Path(__file__).resolve().parent.parent
    sample_dir = backend_dir / "sample_videos"
    sample_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = f"uploaded_{int(time.time())}_{Path(file.filename).name}"
    dest_path = sample_dir / dest_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error("Failed to save uploaded video: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Failed to save video: {str(e)}"})

    logger.info("Uploaded video saved to %s (%d bytes). Switching stream.", dest_path, dest_path.stat().st_size)

    # Register as upload camera channel CAM-UP
    upload_feed = {
        "id": "upload",
        "name": "CAM-UP",
        "sector": f"Custom Upload ({file.filename})",
        "source": str(dest_path),
        "fence_coords": (0.05, 0.60, 0.95, 0.60),
    }
    config.CAMERA_FEEDS["upload"] = upload_feed
    _active_camera_id = "upload"
    _current_source = str(dest_path)
    fence.set_fence_coords(upload_feed["fence_coords"])
    _is_paused = False
    _source_changed = True

    # Reset AI tracker state
    detector_inst = detector.get_detector()
    detector_inst.reset_tracker()
    fence.reset_fence_tracker()

    return {
        "status": "success",
        "filename": file.filename,
        "source": str(dest_path),
        "message": "Video uploaded successfully. Tracking active.",
    }


@app.post("/api/alerts/simulate")
async def simulate_alert():
    """
    Triggers a live demonstration intrusion alert on demand.
    Broadcasts over WebSocket, logs to SQLite, and fires notifications.
    """
    sim_alert = fence.create_simulated_alert()
    await manager.broadcast(sim_alert)
    notifier.send_alert(sim_alert)
    models.log_event(sim_alert)
    logger.info("Simulated breach alert emitted: %s", sim_alert["message"])
    return {"status": "simulated", "alert": sim_alert}


def mjpeg_frame_generator():
    """Yields multipart JPEG frames for video feed streaming."""
    global _latest_jpeg_frame, _is_running
    while _is_running:
        if _latest_jpeg_frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + _latest_jpeg_frame + b"\r\n"
            )
        time.sleep(0.033)


@app.get("/api/video/feed")
def video_feed():
    """
    Live video stream endpoint (MJPEG).
    Renderable directly in HTML <img src="/api/video/feed" /> or canvas.
    """
    return StreamingResponse(
        mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
