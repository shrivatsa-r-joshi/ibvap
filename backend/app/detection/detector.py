"""
Owner: AI Core (IBVAP SIH 26187)

Goal:
Load a pretrained YOLOv8 model (no training needed — yolov8n.pt by default),
run it per frame, track objects persistently across frames, and return a
`detection` message matching docs/schema.md exactly:

{
  "type": "detection",
  "frame_id": int,
  "timestamp": "<ISO8601>",
  "objects": [
    {
      "id": "trk_17",            # stable tracking id, same object -> same id across frames
      "class": "person" | "vehicle",
      "bbox": [x1, y1, x2, y2],  # FRACTIONS of frame width/height, 0-1, NOT raw pixels
      "confidence": 0.0-1.0,
      "crossed_fence": false     # always false here — fence.py sets this, not this file
    }
  ]
}

Hand-off:
app/main.py calls get_detections(frame, frame_id) once per frame, passes the result into fence.py,
then into ws/manager.py and db/models.py.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np

# Ensure backend root is on sys.path for absolute imports
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from ultralytics import YOLO

from app.detection.tracking import (
    CLASS_NAME_MAPPING,
    COCO_TARGET_CLASS_IDS,
    FPSCounter,
    create_detection_message,
    create_tracked_object,
    format_track_id,
    map_class,
    normalize_bbox,
    unnormalize_bbox,
)

try:
    from app import config
except ImportError:
    config = None

# Configure module-level logging
logger = logging.getLogger("ibvap.detection")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


class YOLOVideoDetector:
    """
    Video object detector and persistent tracker utilizing Ultralytics YOLOv8.
    Encapsulates YOLO inference, ByteTrack/BoTSORT tracking, class mapping,
    and schema-compliant message generation.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        tracker_config: Optional[str] = None,
        target_classes: Optional[List[int]] = None,
        device: Optional[str] = None,
    ) -> None:
        """
        Initialize the detector with configurable parameters.

        Args:
            model_path: Path or name of pretrained YOLO model (default: config.YOLO_MODEL_PATH or 'yolov8n.pt').
            conf_threshold: Confidence threshold for detections (default: config.CONFIDENCE_THRESHOLD or 0.45).
            tracker_config: Tracker config file or name (default: config.TRACKER_CONFIG or 'bytetrack.yaml').
            target_classes: COCO class IDs to track (default: person, bicycle, car, motorcycle, bus, truck).
            device: Computing device ('cpu', 'cuda', 'mps', or None for auto-select).
        """
        # Resolve configurations
        self.model_path = model_path or (
            getattr(config, "YOLO_MODEL_PATH", "yolov8n.pt") if config else "yolov8n.pt"
        )
        self.conf_threshold = (
            conf_threshold
            if conf_threshold is not None
            else (getattr(config, "CONFIDENCE_THRESHOLD", 0.28) if config else 0.28)
        )
        self.tracker_config = tracker_config or (
            getattr(config, "TRACKER_CONFIG", "bytetrack.yaml") if config else "bytetrack.yaml"
        )
        self.target_classes = (
            target_classes
            if target_classes is not None
            else list(COCO_TARGET_CLASS_IDS.keys())
        )
        self.device = device or self._detect_best_device()

        logger.info(
            "Initializing YOLOVideoDetector (model=%s, conf=%.2f, tracker=%s, device=%s)",
            self.model_path,
            self.conf_threshold,
            self.tracker_config,
            self.device,
        )

        try:
            self.model = YOLO(self.model_path)
        except Exception as err:
            logger.error("Failed to load YOLO model '%s': %s", self.model_path, err)
            raise

        self.fps_counter = FPSCounter(window_size=30)
        self._total_frames_processed = 0

        logger.info(
            "YOLOVideoDetector initialized successfully. Monitoring classes: %s",
            list(CLASS_NAME_MAPPING.keys()),
        )

    @staticmethod
    def _detect_best_device() -> str:
        """Detect best available acceleration hardware (MPS for Apple Silicon, CUDA, or CPU)."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    @property
    def current_fps(self) -> float:
        """Current processing FPS measured over sliding window."""
        return self.fps_counter.fps

    def reset_tracker(self) -> None:
        """
        Reset persistent tracker state and FPS counter (e.g. when video loops or source changes).
        """
        logger.info("Resetting tracker state and FPS counter.")
        self.fps_counter.reset()
        self.model.predictor = None

    def get_detections(self, frame: Optional[np.ndarray], frame_id: int) -> dict:
        """
        Processes a single video frame, tracks objects persistently, and returns
        the schema-locked detection message dictionary.

        Args:
            frame: a single video frame (OpenCV BGR numpy array) or None.
            frame_id: incrementing integer identifier for this frame.

        Returns:
            dict matching docs/schema.md:
            {
              "type": "detection",
              "frame_id": frame_id,
              "timestamp": "<ISO8601>",
              "objects": [...]
            }
        """
        # Graceful handling of invalid or ended video frames
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            logger.warning("Frame %s is invalid or empty; returning empty detection message.", frame_id)
            return create_detection_message(frame_id=frame_id, objects=[])

        frame_height, frame_width = frame.shape[:2]
        if frame_height <= 0 or frame_width <= 0:
            logger.warning("Frame %s has non-positive dimensions (%dx%d).", frame_id, frame_width, frame_height)
            return create_detection_message(frame_id=frame_id, objects=[])

        t_start = time.perf_counter()

        try:
            # Execute YOLOv8 detection with persistent tracking
            results = self.model.track(
                source=frame,
                persist=True,
                conf=self.conf_threshold,
                classes=self.target_classes,
                tracker=self.tracker_config,
                device=self.device,
                verbose=False,
            )
        except Exception as err:
            logger.error("Error during model.track execution on frame %s: %s", frame_id, err, exc_info=True)
            return create_detection_message(frame_id=frame_id, objects=[])

        elapsed = time.perf_counter() - t_start
        current_fps = self.fps_counter.tick()
        self._total_frames_processed += 1

        detected_objects: List[dict] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                for i, box in enumerate(boxes):
                    # 1. Bounding box in raw pixels [x1, y1, x2, y2]
                    raw_xyxy = box.xyxy[0].tolist()
                    norm_bbox = normalize_bbox(raw_xyxy, frame_width, frame_height)

                    # 2. Class mapping (filter down to "person" or "vehicle", or all if target_classes is None)
                    cls_id = int(box.cls[0].item())
                    cls_name = result.names.get(cls_id, "")
                    allow_all = (self.target_classes is None)
                    target_class = map_class(class_name=cls_name, class_id=cls_id, allow_all=allow_all)
                    if target_class is None:
                        continue

                    # 3. Confidence score
                    conf = float(box.conf[0].item())

                    # 4. Tracking ID
                    if box.id is not None:
                        track_id = int(box.id[0].item())
                        formatted_id = format_track_id(track_id)
                    else:
                        # Fallback if tracker has not assigned an ID yet on initial detection
                        formatted_id = format_track_id(f"det_{cls_id}_{i}")

                    tracked_object = create_tracked_object(
                        track_id=formatted_id,
                        class_name=target_class,
                        bbox=norm_bbox,
                        confidence=conf,
                    )
                    detected_objects.append(tracked_object)

        if self._total_frames_processed % 30 == 0 or len(detected_objects) > 0:
            logger.debug(
                "Frame %d: detected %d objects in %.1f ms (FPS: %.1f)",
                frame_id,
                len(detected_objects),
                elapsed * 1000,
                current_fps,
            )

        return create_detection_message(
            frame_id=frame_id,
            objects=detected_objects,
        )


# Global singleton detector instance for efficient reuse by Person 2 / main.py
_detector_instance: Optional[YOLOVideoDetector] = None


def get_detector(**kwargs) -> YOLOVideoDetector:
    """
    Retrieves or lazily instantiates the global YOLOVideoDetector singleton.
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = YOLOVideoDetector(**kwargs)
    return _detector_instance


def get_detections(frame: Optional[np.ndarray], frame_id: int) -> dict:
    """
    Primary interface called by Person 2 from backend/app/main.py.

    Args:
        frame: a single video frame (as read by OpenCV, BGR numpy array) or None.
        frame_id: incrementing integer for this frame.

    Returns:
        dict matching the `detection` message schema (docs/schema.md):
        {
          "type": "detection",
          "frame_id": 1042,
          "timestamp": "2026-09-05T10:14:32.501Z",
          "objects": [
            {
              "id": "trk_17",
              "class": "person",
              "bbox": [0.32, 0.41, 0.39, 0.68],
              "confidence": 0.91,
              "crossed_fence": false
            }
          ]
        }
    """
    detector = get_detector()
    return detector.get_detections(frame, frame_id)


def open_video_source(source_str: Union[str, int]) -> cv2.VideoCapture:
    """
    Opens a video source (webcam index, video file path, or RTSP stream).
    """
    # Check if integer webcam index
    if isinstance(source_str, int):
        cap = cv2.VideoCapture(source_str)
    elif str(source_str).isdigit():
        cap = cv2.VideoCapture(int(source_str))
    else:
        # File path or stream URL - resolve path robustly
        resolved = config.resolve_video_path(str(source_str)) if config else str(source_str)
        cap = cv2.VideoCapture(resolved)
        if not cap.isOpened() and resolved != str(source_str):
            cap = cv2.VideoCapture(str(source_str))

    if not cap.isOpened():
        raise IOError(f"Unable to open video source: {source_str}")

    return cap


def run_standalone_detector(
    source: Union[str, int],
    model_path: Optional[str] = None,
    conf: Optional[float] = None,
    show_window: bool = False,
    save_output_path: Optional[str] = None,
    max_frames: Optional[int] = None,
) -> None:
    """
    Runs the detector in standalone mode for live testing, demonstration, and verification.
    """
    logger.info("Opening video source: %s", source)
    cap = open_video_source(source)

    detector = YOLOVideoDetector(model_path=model_path, conf_threshold=conf)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0

    logger.info(
        "Video opened: %dx%d @ %.1f FPS (Source: %s)",
        frame_width,
        frame_height,
        fps_video,
        source,
    )

    writer = None
    if save_output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(save_output_path, fourcc, fps_video, (frame_width, frame_height))
        logger.info("Saving output video to: %s", save_output_path)

    frame_id = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.info("Video stream ended or no frame received. Exiting.")
                break

            frame_id += 1
            if max_frames and frame_id > max_frames:
                logger.info("Reached max_frames limit (%d). Exiting.", max_frames)
                break

            # 1. Process frame with detector
            detection_msg = detector.get_detections(frame, frame_id)

            # Output JSON for developer inspection
            if detection_msg["objects"]:
                print(json.dumps(detection_msg, indent=2))

            # Optional visual rendering
            if show_window or writer:
                annotated_frame = frame.copy()
                for obj in detection_msg["objects"]:
                    px_bbox = unnormalize_bbox(obj["bbox"], frame_width, frame_height)
                    x1, y1, x2, y2 = px_bbox
                    cls_color = (0, 255, 0) if obj["class"] == "person" else (255, 128, 0)

                    # Bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), cls_color, 2)

                    # Label tag
                    label = f"{obj['id']} | {obj['class']} {obj['confidence']:.2f}"
                    cv2.putText(
                        annotated_frame,
                        label,
                        (x1, max(15, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        cls_color,
                        2,
                    )

                # Overlay FPS
                fps_text = f"FPS: {detector.current_fps:.1f} | Frame: {frame_id}"
                cv2.putText(
                    annotated_frame,
                    fps_text,
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

                if writer:
                    writer.write(annotated_frame)

                if show_window:
                    cv2.imshow("IBVAP AI Detection & Persistent Tracking", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("User requested exit (key 'q').")
                        break

    finally:
        cap.release()
        if writer:
            writer.release()
        if show_window:
            cv2.destroyAllWindows()
        logger.info("Detector loop finished. Total frames processed: %d", frame_id)


def _resolve_cli_source() -> Union[str, int]:
    """Helper to determine default video source from config or fallback."""
    if config:
        if config.VIDEO_SOURCE == "webcam":
            return 0
        if config.VIDEO_SOURCE == "rtsp" and config.RTSP_URL:
            return config.RTSP_URL
        if config.VIDEO_SOURCE == "sample" and config.SAMPLE_VIDEO_PATH:
            return config.SAMPLE_VIDEO_PATH
    return "0"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBVAP Detection & Persistent Tracking (Person 1)")
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to video file, webcam index ('0'), or RTSP URL",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="YOLO model path or name (e.g. yolov8n.pt)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="Detection confidence threshold (0.0 - 1.0)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show visual playback window with bounding boxes and FPS",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Path to save annotated output video",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum frames to process before stopping",
    )

    args = parser.parse_args()
    source_to_use = args.source if args.source is not None else _resolve_cli_source()

    run_standalone_detector(
        source=source_to_use,
        model_path=args.model,
        conf=args.conf,
        show_window=args.show,
        save_output_path=args.save,
        max_frames=args.max_frames,
    )
