"""
Owner: AI Secondary (Feature 2 — virtual fence intrusion detection)

Goal
----
Take the `objects` list produced by detector.py, check whether each object's
position has crossed the configured virtual fence line, and:
  1. mutate `crossed_fence` to true on any object that just crossed
  2. return a list of `alert` messages (docs/schema.md) — one per NEW crossing
     (don't re-alert on every frame for the same object; only the frame it crosses)

Alert message shape (docs/schema.md):
{
  "type": "alert",
  "alert_id": "<short unique id>",
  "timestamp": "<ISO8601>",
  "object_id": "trk_17",          # must match the detection object's id
  "class": "person" | "vehicle",
  "location": "Fence Line A",
  "severity": "high" | "medium",  # e.g. high for person, medium for vehicle
  "message": "<human-readable description>"
}

Fence line
----------
Read from config.FENCE_LINE_COORDS — (x1, y1, x2, y2) in the same 0-1 fractional
coordinate space as bbox. Use the object's bbox center point and simple line-side
geometry (e.g. cross-product sign) to detect when it moves from one side to the
other. You'll need to remember which side each tracked id was on last frame —
a simple in-memory dict keyed by object id is enough for the demo.

You do not need a second ML model for this — it's coordinate geometry on top of
detector.py's output.
"""

def check_fence_crossings(objects: list[dict]) -> list[dict]:
    """
    Args:
        objects: the `objects` list from a detection message (mutated in place —
                 sets crossed_fence=True on any object that just crossed)

    Returns:
        list of new `alert` message dicts (may be empty most frames)
    """
    # TODO: implement line-crossing check + alert generation
    raise NotImplementedError
