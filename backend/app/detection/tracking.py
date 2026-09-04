"""
Owner: AI Core (IBVAP SIH 26187)

Tracking utilities, data validation, and locked schema formatters.
NOTE: Per architecture requirements, this file does NOT import or touch
YOLO directly. Only detector.py interacts with the ML model.
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, Union


# Mapping of COCO dataset class names to target categories
CLASS_NAME_MAPPING = {
    # Person
    "person": "person",

    # Vehicles mapped to "vehicle"
    "car": "vehicle",
    "motorcycle": "vehicle",
    "bus": "vehicle",
    "truck": "vehicle",
    "bicycle": "vehicle",
    "train": "vehicle",
    "boat": "vehicle",
    "airplane": "vehicle",
}

# Standard COCO class IDs in YOLOv8 for target tracking
COCO_TARGET_CLASS_IDS = {
    0: "person",
    1: "vehicle",  # bicycle
    2: "vehicle",  # car
    3: "vehicle",  # motorcycle
    4: "vehicle",  # airplane
    5: "vehicle",  # bus
    6: "vehicle",  # train
    7: "vehicle",  # truck
    8: "vehicle",  # boat
}


def map_class(
    class_name: Optional[str] = None,
    class_id: Optional[int] = None,
    allow_all: bool = False,
) -> Optional[str]:
    """
    Maps a detected class name or COCO ID to 'person', 'vehicle', or None (ignored).
    If allow_all=True, returns the original class name for any detected object.
    """
    if class_name is not None:
        lowered = class_name.strip().lower()
        if lowered in CLASS_NAME_MAPPING:
            return CLASS_NAME_MAPPING[lowered]
        if allow_all:
            return lowered
        return None
    if class_id is not None:
        if class_id in COCO_TARGET_CLASS_IDS:
            return COCO_TARGET_CLASS_IDS[class_id]
        if allow_all:
            return f"class_{class_id}"
        return None
    return None


def normalize_bbox(
    box_xyxy: Union[List[float], Tuple[float, float, float, float]],
    frame_width: int,
    frame_height: int,
    precision: int = 4,
) -> List[float]:
    """
    Normalizes bounding box pixel coordinates [x1, y1, x2, y2] to 0-1 fractional coordinates.
    Guarantees clamped coordinates between 0.0 and 1.0.

    Args:
        box_xyxy: [x1, y1, x2, y2] raw pixel coordinates
        frame_width: width of the frame in pixels
        frame_height: height of the frame in pixels
        precision: number of decimal digits to round to

    Returns:
        [x1, y1, x2, y2] normalized to 0.0 - 1.0
    """
    if frame_width <= 0 or frame_height <= 0:
        return [0.0, 0.0, 0.0, 0.0]

    x1, y1, x2, y2 = box_xyxy

    norm_x1 = max(0.0, min(1.0, float(x1) / frame_width))
    norm_y1 = max(0.0, min(1.0, float(y1) / frame_height))
    norm_x2 = max(0.0, min(1.0, float(x2) / frame_width))
    norm_y2 = max(0.0, min(1.0, float(y2) / frame_height))

    # Ensure ordering is preserved
    if norm_x2 < norm_x1:
        norm_x1, norm_x2 = norm_x2, norm_x1
    if norm_y2 < norm_y1:
        norm_y1, norm_y2 = norm_y2, norm_y1

    return [
        round(norm_x1, precision),
        round(norm_y1, precision),
        round(norm_x2, precision),
        round(norm_y2, precision),
    ]


def unnormalize_bbox(
    bbox: Union[List[float], Tuple[float, float, float, float]],
    frame_width: int,
    frame_height: int,
) -> Tuple[int, int, int, int]:
    """
    Converts 0-1 fractional coordinates back to pixel coordinates for display/drawing.
    """
    x1, y1, x2, y2 = bbox
    return (
        int(round(x1 * frame_width)),
        int(round(y1 * frame_height)),
        int(round(x2 * frame_width)),
        int(round(y2 * frame_height)),
    )


def format_track_id(raw_id: Union[int, str]) -> str:
    """
    Ensures track IDs match the schema format 'trk_<id>' (e.g. 'trk_17').
    """
    id_str = str(raw_id).strip()
    if id_str.startswith("trk_"):
        return id_str
    return f"trk_{id_str}"


def get_iso_timestamp() -> str:
    """
    Returns current UTC timestamp formatted as ISO-8601 with millisecond precision
    ending with 'Z' (e.g. '2026-09-05T10:14:32.501Z').
    """
    now = datetime.now(timezone.utc)
    # Format with microseconds, then trim to 3 fractional digits (milliseconds)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def create_tracked_object(
    track_id: Union[int, str],
    class_name: str,
    bbox: List[float],
    confidence: float,
) -> dict:
    """
    Constructs an object entry strictly adhering to docs/schema.md:
    {
      "id": "trk_17",
      "class": "person" | "vehicle",
      "bbox": [0.32, 0.41, 0.39, 0.68],
      "confidence": 0.91,
      "crossed_fence": false
    }
    """
    if class_name not in ("person", "vehicle"):
        mapped = map_class(class_name=class_name)
        class_name = mapped if mapped else "object"

    return {
        "id": format_track_id(track_id),
        "class": class_name,
        "bbox": bbox,
        "confidence": round(float(confidence), 2),
        "crossed_fence": False,  # Always False initially. fence.py alters this.
    }


def create_detection_message(
    frame_id: int,
    objects: List[dict],
    timestamp: Optional[str] = None,
) -> dict:
    """
    Constructs the root detection message adhering to docs/schema.md:
    {
      "type": "detection",
      "frame_id": 1042,
      "timestamp": "2026-09-05T10:14:32.501Z",
      "objects": [...]
    }
    """
    return {
        "type": "detection",
        "frame_id": int(frame_id),
        "timestamp": timestamp or get_iso_timestamp(),
        "objects": objects,
    }


class FPSCounter:
    """
    Sliding-window FPS counter for accurate, smooth FPS measurement.
    """

    def __init__(self, window_size: int = 30) -> None:
        self.window_size = max(1, window_size)
        self.timestamps: deque[float] = deque(maxlen=self.window_size)
        self._last_tick_time: float = 0.0

    def tick(self) -> float:
        """
        Record a frame completion time and return current calculated FPS.
        """
        now = time.perf_counter()
        self.timestamps.append(now)
        self._last_tick_time = now
        return self.fps

    @property
    def fps(self) -> float:
        """
        Calculates FPS over the current sliding window.
        """
        if len(self.timestamps) < 2:
            return 0.0
        duration = self.timestamps[-1] - self.timestamps[0]
        if duration <= 0:
            return 0.0
        return round((len(self.timestamps) - 1) / duration, 1)

    def reset(self) -> None:
        """Reset the FPS counter."""
        self.timestamps.clear()
        self._last_tick_time = 0.0
