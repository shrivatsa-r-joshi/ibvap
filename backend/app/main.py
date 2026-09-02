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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.ws.manager import ConnectionManager
from app.detection import detector, fence
from app.db import models
from app.alerts import notifier
from app import config

app = FastAPI(title="IBVAP")
manager = ConnectionManager()


@app.on_event("startup")
async def startup():
    models.init_db()
    # TODO: kick off the video processing loop as a background task


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; frontend doesn't need to send anything meaningful
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# TODO: implement the video processing loop:
#   - open VIDEO_SOURCE (sample file, webcam, or RTSP per config.VIDEO_SOURCE)
#   - for each frame: detector.get_detections() -> fence.check_fence_crossings()
#     -> manager.broadcast(detection_message)
#     -> for each new alert: manager.broadcast(alert), notifier.send_alert(alert), models.log_event(alert)
#     -> models.log_event(detection_message) if it has objects
