# Data Schema — v1 (locked)

This is the contract every module codes against. If it needs to change, flag it in the group chat first
— `detector.py`, `fence.py`, `main.py`, `ws/manager.py`, `db/models.py`, `socket.js`, `VideoPanel.jsx`,
and `AlertsFeed.jsx` all depend on these exact shapes.

All messages travel over one WebSocket channel (`/ws/live`) as JSON. The frontend routes on `"type"`.

## 1. `detection` message

Produced by `detector.py` (and enriched by `fence.py`) once per processed frame.

```json
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
    },
    {
      "id": "trk_18",
      "class": "vehicle",
      "bbox": [0.55, 0.30, 0.78, 0.52],
      "confidence": 0.87,
      "crossed_fence": false
    }
  ]
}
```

**Field notes**
- `bbox` is `[x1, y1, x2, y2]` as **fractions of frame width/height (0–1)**, not raw pixels. This means
  the frontend can draw boxes correctly regardless of the video's actual resolution — agree on this now
  so nobody has to convert coordinates later.
- `id` is a stable tracking ID (same object keeps the same `id` across frames). Needed so the frontend
  doesn't flicker boxes and so `fence.py` can tell "has this specific object already been flagged."
- `class` is `"person"` or `"vehicle"` for the demo scope. Leave room to add `"face"` later if time allows.
- `crossed_fence` starts `false` from `detector.py` and is set `true` by `fence.py` once that object's
  position crosses the configured line. `detector.py` should not set this field itself.

## 2. `alert` message

Produced by `fence.py` the moment an object's `crossed_fence` flips to `true`. Sent once per
crossing event (not repeated every frame).

```json
{
  "type": "alert",
  "alert_id": "a1b2c3d4",
  "timestamp": "2026-09-05T10:14:33.010Z",
  "object_id": "trk_17",
  "class": "person",
  "location": "Fence Line A",
  "severity": "high",
  "message": "Person crossed restricted boundary near Fence Line A"
}
```

**Field notes**
- `alert_id` — generate a short unique ID (e.g. `uuid4().hex[:8]`) so the DB and the frontend can
  de-duplicate if the message is ever sent twice.
- `object_id` must match the `id` from the `detection` message that triggered it — this is how the
  frontend can (optionally) highlight the specific box that caused the alert.
- `severity` — use `"high"` for person crossings, `"medium"` for vehicle crossings, to start.
- This exact object is what `alerts/notifier.py` consumes to fire the SMS/email, and what
  `db/models.py` logs as a row.

## 3. Database row (SQLite, `events` table)

Both `detection` and `alert` messages get logged, but a `detection` message is usually only logged when
it contains at least one object (don't flood the DB with empty frames).

| column | type | notes |
|---|---|---|
| `id` | integer, autoincrement | |
| `type` | text | `"detection"` or `"alert"` |
| `timestamp` | text (ISO 8601) | |
| `object_id` | text, nullable | |
| `class` | text, nullable | |
| `payload` | text (JSON) | the full message, for anything not worth its own column |

## 4. Alert delivery (SMS/email)

`alerts/notifier.py` doesn't define a new schema — it just consumes the `alert` message above and maps
it to whatever Twilio/SendGrid needs. Suggested SMS text:

```
[IBVAP ALERT] {severity} — {class} detected at {location}, {timestamp}
```

## 5. Config the AI/fence modules need (see `.env.example`)

- `FENCE_LINE_COORDS` — the virtual fence line, as two points: `x1,y1,x2,y2`, in the same 0–1 fractional
  coordinate space as `bbox` above, so it lines up regardless of video resolution.
- `VIDEO_SOURCE`, `SAMPLE_VIDEO_PATH`, `RTSP_URL` — where frames come from.

---
**Versioning:** this is schema v1. If a field must change during integration, update this file in the
same commit/PR as the code change, and mention it in the team chat — do not let the doc and the code
drift apart.
