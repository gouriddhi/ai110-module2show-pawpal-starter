# CLAUDE.md

## Project
PawPal+ — a Streamlit app that helps a pet owner plan daily pet-care tasks
based on time available, task priority, and owner preferences. Course project
(AI110 Module 2): design UML first → implement Python logic → wire into UI → test.

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run app: `streamlit run app.py`
- Tests: `pytest` (coverage: `pytest --cov`)

## Structure
- `app.py` — Streamlit UI. Tasks live in `st.session_state.tasks` as
  `{"title", "duration_minutes", "priority"}` dicts. "Generate schedule" button
  is a stub; it should call the scheduler.
- `diagrams/uml.mmd` — Mermaid class diagram (keep in sync with real code; filename is fixed for grading).
- `reflection.md`, `ai_interactions.md` — student write-ups (templates).
- Scheduling logic and tests do not exist yet.

## Core user actions
1. Enter owner + pet info (name, species, available time/preferences).
2. Add/edit tasks (title, duration, priority required).
3. Generate a daily plan that orders tasks by constraints and explains why.

## Conventions
- Keep scheduling logic in Python classes separate from `app.py`; the UI only calls them.
- Priorities: "low" | "medium" | "high".
- Add pytest tests for key scheduling behavior (priority ordering, time limits, conflicts).
- Update README sections (Sample Output, Smarter Scheduling, Demo Walkthrough) as features land.
