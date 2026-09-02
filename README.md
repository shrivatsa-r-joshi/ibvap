# IBVAP — Intelligent Border Video Analytics Platform
**SIH26187** · Software Solution for converting CCTV Network into Comprehensive Surveillance and Monitoring System

Team: `<TEAM NAME>` · Demo date: **Saturday, 5 September 2026**

---

## 1. The pitch, in one paragraph

Border CCTV records and displays video, but someone still has to watch the screen to catch anything.
IBVAP is a software-only layer that sits on top of existing IP cameras and makes them intelligent —
detecting people and vehicles, tracking them, and firing a real-time alert the moment someone crosses
a restricted line. No proprietary hardware, no camera replacement.

## 2. What the demo actually shows live

We are **not** trying to build all eight capabilities from the problem statement in three days. We are
building two, extremely well, and presenting the rest as designed/roadmap. This is a deliberate scope
decision — judges reward a convincing, reliable MVP over a fragile full-stack demo.

| # | Feature | Status on demo day |
|---|---|---|
| 1 | Human & vehicle detection + tracking (YOLOv8, pretrained) | **Live** |
| 2 | Virtual fence intrusion detection + real-time alert (SMS/email + dashboard) | **Live** |
| 3 | Face detection | Roadmap card on dashboard |
| 4 | ANPR | Roadmap card on dashboard (attempt live if time allows, pre-recorded fallback clip ready) |
| 5 | Night-time detection | Roadmap card on dashboard |
| 6 | Suspicious activity detection | Roadmap card on dashboard |

Features 1 and 2 share the *same* YOLOv8 pipeline — the fence check is pure geometry on top of
detection output, not a second model. That's what keeps this achievable in three days.

## 3. Repo layout

```
ibvap/
├── README.md              you are here
├── ARCHITECTURE.md        full breakdown of every folder/file + who owns it
├── CONTRIBUTING.md        git workflow for the team
├── .env.example           config template (copy to .env, fill in, never commit .env)
├── docs/
│   ├── schema.md          the data contract — READ THIS BEFORE WRITING CODE
│   ├── demo-script.md     narration template for the live run
│   └── team-checklist.pdf offline copy of the day-by-day task tracker
├── backend/               FastAPI service: detection, fence logic, alerts, DB, websocket
└── frontend/               React dashboard: video panel, live alerts, roadmap cards
```

Full explanation of each file: see **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

## 4. The most important rule

**[docs/schema.md](./docs/schema.md) is the contract.** It defines the exact JSON shape that flows
between detection → fence logic → backend → websocket → frontend → alerts. Everyone's code — however
it gets written, including with AI tools — must produce and consume these exact shapes. If six people
each freelance their own JSON format, integration on day 3 will eat the whole day. If everyone codes
against the shared schema from hour one, integration is just plugging modules together.

If you think a field needs to change, say so in the group chat before changing it — three other files
depend on it.

## 5. Getting started

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in your values
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm create vite@latest . -- --template react   # first time only, if not already scaffolded
npm install
npm run dev
```

## 6. Team & ownership

| Folder / area | Owner | Feature |
|---|---|---|
| `backend/app/detection/detector.py` | AI Core | Feature 1 — detection & tracking |
| `backend/app/detection/fence.py` | AI Secondary | Feature 2 — virtual fence logic |
| `backend/app/db/`, `backend/app/ws/`, `backend/app/main.py` | Backend | Glue: DB, websocket, app wiring |
| `frontend/src/` | Frontend | Dashboard UI |
| `backend/app/alerts/` | Integration | SMS/email alerts, ANPR attempt |
| `docs/demo-script.md`, PPT, QA | PPT/Script/QA | Narration, slides, backup video, rehearsal |

Full day-by-day tasks per role: `docs/team-checklist.pdf`.

## 7. Git workflow

See **[CONTRIBUTING.md](./CONTRIBUTING.md)**.

## 8. Video source

Not locked yet — `.env.example` supports `sample`, `webcam`, or `rtsp` via `VIDEO_SOURCE`, so switching
later doesn't require code changes. Default to a recorded sample clip for reliability; only move to a
live webcam or real camera feed if it's tested well before demo day.
