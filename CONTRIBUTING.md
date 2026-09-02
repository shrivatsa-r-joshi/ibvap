# Git Workflow

You're all comfortable with git, so this is short — just the conventions we're all using so a 3-day
sprint with 6 people doesn't turn into merge-conflict archaeology.

## Branches

- `main` — always demo-able. Don't push broken code directly to it once integration starts (Day 2 onward).
- Feature branches: `feature/<role>-<short-desc>`, e.g. `feature/ai-core-yolo-integration`,
  `feature/frontend-alerts-feed`.

## Day 1 (setup, isolated work)

Everyone can commit fairly freely inside their own folder (see ownership table in `README.md`). Low
conflict risk since you're mostly touching different files.

## Day 2 (integration)

This is where `main.py`, `App.jsx`, `docs/schema.md`, and `ws/manager.py` get touched by more than one
person. For these specific shared files:
1. Pull latest `main` before starting.
2. Open a PR even if it's small — someone else does a 2-minute glance, not a deep review.
3. Merge fast. The goal is visibility, not process for its own sake.

Everything else (your own module's internals) — commit directly, push often.

## Day 3 (polish + freeze)

Feature-freeze by midday if possible. After that, only bug fixes — no new scope. This is also when
`docs/schema.md` should stop changing entirely.

## Commit messages

Doesn't need to be fancy — `[ai-core] add tracking to detector.py` is enough. Prefix with your area so
the log is scannable when someone's debugging integration issues at 11pm.

## Daily sync

Given the timeline, a 10-minute stand-up each morning (what did you finish, what's blocking you, does
anything touch the shared schema today) will save more time than it costs.
