"""
Owner: AI Secondary (Feature 2 — virtual fence intrusion detection)

Coordinate geometry line-crossing and bounding-box contact/tampering intrusion detection
based on detector.py output.
"""
from __future__ import annotations

import logging
import time
from uuid import uuid4
from typing import Dict, List, Optional, Set, Tuple

from app import config
from app.detection.tracking import get_iso_timestamp

logger = logging.getLogger("trinetra.fence")

# In-memory tracking of object positions relative to the fence line
# object_id -> previous sign (1 for positive side, -1 for negative side, 0 on line)
_previous_sides: Dict[str, int] = {}
# object_id -> timestamp of last emitted alert
_last_alert_time: Dict[str, float] = {}
# Dynamic fence coordinates (defaults to config.FENCE_LINE_COORDS)
_active_fence_coords: Optional[Tuple[float, float, float, float]] = None


def get_fence_coords() -> Tuple[float, float, float, float]:
    """Returns current active fence line coordinates (x1, y1, x2, y2)."""
    global _active_fence_coords
    if _active_fence_coords is not None:
        return _active_fence_coords
    return getattr(config, "FENCE_LINE_COORDS", (0.05, 0.52, 0.95, 0.52))


def set_fence_coords(coords: Tuple[float, float, float, float]) -> None:
    """Updates active fence coordinates dynamically from frontend/control."""
    global _active_fence_coords
    if len(coords) == 4:
        _active_fence_coords = coords
        logger.info("Updated virtual fence line coordinates to: %s", coords)
        reset_fence_tracker()


def _get_line_side(px: float, py: float, line: Tuple[float, float, float, float]) -> int:
    """
    Computes which side of the directed line segment (x1, y1) -> (x2, y2) the point (px, py) is on.
    Returns 1 for one side, -1 for the other, 0 if on the line.
    """
    x1, y1, x2, y2 = line
    cross_product = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if cross_product > 1e-5:
        return 1
    elif cross_product < -1e-5:
        return -1
    return 0


def _box_intersects_fence(bbox: List[float], fence: Tuple[float, float, float, float]) -> bool:
    """
    Determines if a bounding box [x1, y1, x2, y2] intersects or directly tampers
    with the fence line segment (fx1, fy1) -> (fx2, fy2).
    Essential for detecting wire-cutting and fence tampering when the person's hands
    or body touch the wire even before feet cross.
    """
    bx1, by1, bx2, by2 = bbox
    fx1, fy1, fx2, fy2 = fence

    min_fx, max_fx = min(fx1, fx2), max(fx1, fx2)
    min_fy, max_fy = min(fy1, fy2), max(fy1, fy2)

    # 1. Broad phase: horizontal & vertical overlap
    if bx2 < min_fx or bx1 > max_fx:
        return False

    # 2. Check if the fence height at the box's horizontal position passes through the box
    box_cx = (bx1 + bx2) / 2.0
    if abs(fx2 - fx1) > 1e-6:
        t = max(0.0, min(1.0, (box_cx - fx1) / (fx2 - fx1)))
        fence_y = fy1 + t * (fy2 - fy1)
        # Expand tolerance slightly (3% frame height) for hands / tools touching wire
        if (by1 - 0.03) <= fence_y <= (by2 + 0.03):
            return True

    # 3. Check corner sign difference (box crosses the line)
    corners = [(bx1, by1), (bx2, by1), (bx2, by2), (bx1, by2)]
    sides = [_get_line_side(px, py, fence) for px, py in corners]
    if min(sides) < 0 and max(sides) > 0:
        return True

    return False


def reset_fence_tracker() -> None:
    """Resets fence memory when video stream restarts or re-initializes."""
    _previous_sides.clear()
    _last_alert_time.clear()


def create_simulated_alert(target_id: str = "trk_sim_1", target_class: str = "person", location: str = "Perimeter Sector A") -> dict:
    """Creates a demonstration alert on demand for verification/testing."""
    severity = "critical" if target_class == "person" else "high"
    return {
        "type": "alert",
        "alert_id": uuid4().hex[:8],
        "timestamp": get_iso_timestamp(),
        "object_id": target_id,
        "class": target_class,
        "location": location,
        "severity": severity,
        "message": f"Perimeter Wire Breach: {target_class.capitalize()} ({target_id}) tampering with boundary fence at {location}",
    }


def check_fence_crossings(objects: List[dict], location: str = "Perimeter Sector A") -> List[dict]:
    """
    Detects fence crossings, wire tampering, and boundary collisions.

    Args:
        objects: the `objects` list from a detection message (mutated in place —
                 sets crossed_fence=True on any object intersecting or crossing the fence)
        location: human-readable sector description for the alert

    Returns:
        list of new `alert` message dicts
    """
    fence_coords = get_fence_coords()
    if len(fence_coords) != 4:
        return []

    alerts: List[dict] = []
    current_ids = set()
    now = time.time()

    for obj in objects:
        obj_id = obj.get("id")
        if not obj_id:
            continue

        current_ids.add(obj_id)
        bbox = obj.get("bbox", [0, 0, 0, 0])
        obj_class = obj.get("class", "object")

        # 1. Bounding box intersection / wire contact check (Tampering)
        intersects = _box_intersects_fence(bbox, fence_coords)

        # 2. Centroid and bottom-feet line crossing check
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = bbox[3]
        current_side = _get_line_side(cx, cy, fence_coords)
        crossed_line = False

        if obj_id in _previous_sides:
            prev_side = _previous_sides[obj_id]
            if prev_side != 0 and current_side != 0 and prev_side != current_side:
                crossed_line = True

        _previous_sides[obj_id] = current_side

        is_breach = intersects or crossed_line

        if is_breach:
            obj["crossed_fence"] = True

            # Rate-limit alerts to once every 5 seconds per object
            last_alert = _last_alert_time.get(obj_id, 0.0)
            if now - last_alert > 5.0:
                _last_alert_time[obj_id] = now
                severity = "critical" if obj_class == "person" else "high"
                action_text = "cutting/tampering with razor wire" if intersects else "crossed boundary tripwire"
                alert_msg = {
                    "type": "alert",
                    "alert_id": uuid4().hex[:8],
                    "timestamp": get_iso_timestamp(),
                    "object_id": obj_id,
                    "class": obj_class,
                    "location": location,
                    "severity": severity,
                    "message": f"Perimeter Wire Breach: {obj_class.capitalize()} ({obj_id}) {action_text} at {location}",
                }
                alerts.append(alert_msg)
                logger.warning("VIRTUAL FENCE BREACH: %s", alert_msg["message"])

    # Garbage collection of disappeared objects
    if len(_previous_sides) > 200:
        stale_ids = [oid for oid in _previous_sides if oid not in current_ids]
        for oid in stale_ids[:50]:
            _previous_sides.pop(oid, None)
            _last_alert_time.pop(oid, None)

    return alerts
