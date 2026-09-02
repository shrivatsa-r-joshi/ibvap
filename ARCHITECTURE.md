# Architecture

This is the document to walk the team through when you brief them. It explains what every folder is
for, who owns it, and — most importantly — how data moves through the system so nobody builds a piece
that doesn't fit the others.

## Data flow (the story of one detected event)

```
Camera / sample video
        │
        ▼
detection/detector.py  ──►  produces a "detection" message (docs/schema.md)
        │
        ▼
detection/fence.py     ──►  reads detection objects, checks line-crossing,
        │                   produces an "alert" message when triggered
        ▼
app/main.py             ──►  wires detector + fence together, hands both
        │                    message types to the websocket manager and the DB
        ├──────────────┬────────────────┐
        ▼              ▼                ▼
   ws/manager.py    db/models.py    alerts/notifier.py
   (push to UI)     (persist log)   (send SMS/email on "alert" only)
        │
        ▼
frontend (VideoPanel + AlertsFeed) — renders live boxes and the alert feed
```

Everything left of the fork produces or transforms data. Everything right of the fork just *consumes*
it. That split is deliberate: the AI Core and AI Secondary people never need to know FastAPI, React, or
Twilio exists — they just need to emit the JSON shapes in `docs/schema.md`. The Backend and Frontend
people never need to know anything about YOLO — they just need to consume those same shapes.

## Folder-by-folder

### `backend/app/detection/`
- **`detector.py`** — Owner: **AI Core**. Loads YOLOv8 (pretrained, no training needed), runs it on
  each video frame, tracks objects across frames, and outputs a `detection` message per `docs/schema.md`.
  This is the only file that touches the ML model directly.
- **`fence.py`** — Owner: **AI Secondary**. Takes the object list from `detector.py`, checks whether
  each object's position has crossed the configured fence line (pure coordinate geometry, no ML), and
  produces an `alert` message when it has. Also owns face detection if time allows — kept in this folder
  since it's part of the same per-frame analysis step.

### `backend/app/alerts/`
- **`notifier.py`** — Owner: **Integration**. Listens for `alert` messages and sends an SMS (Twilio) and/or
  email (SendGrid). This is the only file that touches third-party alert APIs — keeps API keys and retry
  logic in one place.

### `backend/app/db/`
- **`models.py`** — Owner: **Backend**. SQLite table(s) that log every `detection` and `alert` event, so
  you have a history to show ("here's everything the system caught today").

### `backend/app/ws/`
- **`manager.py`** — Owner: **Backend**. Keeps track of connected frontend clients and broadcasts every
  `detection`/`alert` message to them in real time over a single WebSocket connection.

### `backend/app/main.py`
- Owner: **Backend**. The FastAPI entry point. Starts the video loop, calls `detector.py` then
  `fence.py` per frame, and hands the result to both `ws/manager.py` and `db/models.py`. This is the
  file that "wires everything together" — expect Backend to be pairing with AI Core/Secondary here
  during the integration day.

### `backend/sample_videos/`
- Gitignored (video files are large). Drop your test clips here locally; share via a Drive link in the
  team chat rather than committing them.

### `frontend/src/`
- **`components/VideoPanel.jsx`** — Owner: **Frontend**. Renders the video with live bounding boxes
  drawn from incoming `detection` messages.
- **`components/AlertsFeed.jsx`** — Owner: **Frontend**. Scrolling feed of incoming `alert` messages.
- **`components/RoadmapCard.jsx`** — Owner: **Frontend**. Static, clearly-labelled cards for ANPR,
  face recognition, and night-mode — shown so the platform reads as complete even though those aren't
  live for this demo.
- **`api/socket.js`** — Owner: **Frontend**. Opens the WebSocket connection to the backend and routes
  incoming messages by their `type` field to the right component.

### `docs/`
- **`schema.md`** — the data contract. Read before writing any code that produces or consumes messages.
- **`demo-script.md`** — narration template for the live run, owned by PPT/Script/QA.
- **`team-checklist.pdf`** — offline copy of the day-by-day task tracker.

## Why this structure keeps a beginner + AI-assisted team safe

1. **Ownership maps to folders, not files scattered everywhere.** Two people rarely need to edit the
   same file, which matters a lot when most of the code is AI-generated — merge conflicts in
   AI-generated code are painful to resolve by hand.
2. **The schema is the only thing that must never silently change.** Everything else is an
   implementation detail inside one person's folder.
3. **`main.py` and `App.jsx` are the two files everyone eventually touches.** Treat changes to those as
   "shout in the group chat first," per `CONTRIBUTING.md`.
