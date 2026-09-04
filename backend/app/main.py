"""
Owner: Backend (integrates everyone else's modules — expect to pair with AI Core /
AI Secondary here during Day 2 integration)

Goal
----
FastAPI entry point. Responsibilities:
  1. Expose the `/ws/live` WebSocket endpoint (frontend connects here).
  2. Run the video loop: read frames from the configured source (config.VIDEO_SOURCE),
     call detection.detector.get_detections() per frame, then
     detection.fence.check_fence_crossings() on the result.
  3. Broadcast every detection message via ws.manager, and every alert message via
     both ws.manager AND alerts.notifier.send_alert().
  4. Log every detection (with objects) and every alert via db.models.log_event().

This file is the one place where every other module gets wired together — see
ARCHITECTURE.md for the full data flow diagram.
"""
import asyncio
import logging
from datetime import datetime, timezone

# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.ws.manager import ConnectionManager
from app.detection import detector, fence
from app.db import models
from app.alerts import notifier
from app import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ibvap.main")

app = FastAPI(title="IBVAP")
manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Simple health check so you can verify the server is running."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.on_event("startup")
async def startup():
    models.init_db()
    asyncio.create_task(video_loop())
    logger.info("IBVAP backend started")


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def video_loop():
    """
    Main processing loop:
      1. Open the video source
      2. Read frames
      3. For each frame: detector → fence → broadcast + log
    """
    # Resolve video source
    if config.VIDEO_SOURCE == "sample":
        source = config.SAMPLE_VIDEO_PATH
    elif config.VIDEO_SOURCE == "webcam":
        source = 0
    elif config.VIDEO_SOURCE == "rtsp":
        source = config.RTSP_URL
    else:
        logger.error(f"Unknown VIDEO_SOURCE: {config.VIDEO_SOURCE}")
        return

    logger.info(f"Opening video source: {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error(f"Cannot open video source: {source}")
        return

    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Video ended or frame read failed, restarting...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop sample video
                ret, frame = cap.read()
                if not ret:
                    logger.error("Cannot read any frames, stopping video loop")
                    break

            frame_id += 1

            try:
                # --- Step 1: Get detections from AI module ---
                detection_msg = detector.get_detections(frame, frame_id)

                # --- Step 2: Check fence crossings ---
                alerts = fence.check_fence_crossings(detection_msg.get("objects", []))

                # --- Step 3: Broadcast detection to all connected frontends ---
                await manager.broadcast(detection_msg)

                # --- Step 4: Log detection if it has objects ---
                if detection_msg.get("objects"):
                    models.log_event(detection_msg)

                # --- Step 5: Handle each alert ---
                for alert in alerts:
                    await manager.broadcast(alert)
                    models.log_event(alert)
                    try:
                        notifier.send_alert(alert)
                    except Exception as e:
                        logger.error(f"Notifier failed: {e}")

            except NotImplementedError:
                # AI modules not ready yet — this is expected on Day 1
                # Generate a fake detection so we can test the pipeline
                detection_msg = {
                    "type": "detection",
                    "frame_id": frame_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "objects": [
                        {
                            "id": "trk_1",
                            "class": "person",
                            "bbox": [0.3, 0.4, 0.5, 0.7],
                            "confidence": 0.92,
                            "crossed_fence": False,
                        }
                    ],
                }
                await manager.broadcast(detection_msg)
                models.log_event(detection_msg)

            except Exception as e:
                logger.error(f"Error processing frame {frame_id}: {e}")

            # ~10 FPS to avoid flooding (adjust as needed)
            await asyncio.sleep(0.1)

    finally:
        cap.release()
        logger.info("Video capture released")
