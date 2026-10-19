# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🛠️ Implementation Summary

The scheduling logic lives in `pawpal_system.py` and is built from four classes:

- **`Task`**: a single care activity (title, description, duration, priority, frequency, completion status). A task can have a fixed `scheduled_time` (e.g. meds at 09:00) or a flexible `preferred_time` of day. It knows when it was last completed, so daily tasks reappear the next day and weekly tasks after seven days.
- **`Pet`**: a pet's details plus its list of tasks. Adding a task tags it with the pet's name so the plan can show whose task it is.
- **`Owner`**: the person, their available minutes and day window (default 08:00–20:00), and their pets. `get_all_tasks()` gathers every pet's tasks into one list.
- **`Scheduler`**: the planner. It reads tasks from `Owner.get_all_tasks()`, so it works across all pets, then builds the day in three steps:
  1. **Sort** by priority (high first), then by shorter duration.
  2. **Filter** out tasks already done for the period, and anything that no longer fits in the owner's time budget.
  3. **Assign slots**: fixed-time tasks go at their exact time; flexible tasks fill the earliest free gap at or after their preferred time.

  Every skipped task is recorded with a reason, `explain_choice()` describes why any task was scheduled or skipped, and `detect_conflicts()` reports overlapping fixed-time tasks.

`main.py` builds a sample owner with two pets and prints today's schedule, and `tests/test_pawpal.py` covers the key behaviors. The Streamlit UI in `app.py` is not yet connected to these classes.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Today's Schedule for Jordan
==================================================
08:00-08:10  Luna   Breakfast        [medium]  fixed at 08:00
08:10-08:40  Mochi  Morning walk     [high]    high priority, preferred morning
09:00-09:05  Mochi  Heartworm meds   [high]    fixed at 09:00
18:00-18:15  Luna   Laser play       [medium]  fixed at 18:00

Skipped
--------------------------------------------------
Luna   Full grooming    not enough time: needs 90 min, 60 min left
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
