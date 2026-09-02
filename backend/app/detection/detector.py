"""
Owner: AI Core (Feature 1 — human & vehicle detection + tracking)

Goal
----
Load a pretrained YOLOv8 model (no training needed — `yolov8n.pt` or `yolov8s.pt`
from ultralytics is enough), run it per frame, track objects across frames, and
return a `detection` message matching docs/schema.md exactly:

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
    },
    ...
  ]
}

Suggested approach
-------------------
- `ultralytics.YOLO("yolov8n.pt")` for detection.
- Use the model's built-in tracker (`model.track(..., persist=True)`) to get stable
  IDs for free instead of writing your own tracker.
- Map YOLO's COCO classes down to just "person" and "vehicle" (car/truck/bus/motorcycle -> "vehicle").
- Convert YOLO's pixel bbox to fractional coords by dividing by frame width/height.

Hand-off
--------
`app/main.py` calls this once per frame, passes the result into `fence.py`, then
into `ws/manager.py` and `db/models.py`. You shouldn't need to touch those files —
just make sure your return value matches the schema above exactly.
"""

def get_detections(frame, frame_id: int) -> dict:
    """
    Args:
        frame: a single video frame (as read by OpenCV, BGR numpy array)
        frame_id: incrementing integer for this frame

    Returns:
        dict matching the `detection` message schema above.
    """
    # TODO: implement using ultralytics YOLOv8 + tracking
    raise NotImplementedError
