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

## ✨ Features

**Planning the day**
- **Priority-first planning:** tasks claim time in priority order (high → medium → low). Among equal priorities, shorter tasks go first, so more of them fit. *(`Scheduler.sort_tasks()`)*
- **Time-budget filtering:** the plan never uses more than the owner's available minutes or the length of their day. If a task gets past the budget check but can't be placed, its minutes go to the next task that fits. *(`Scheduler.filter_tasks()`, `Scheduler.generate_plan()`)*
- **Fixed and flexible time slots:** tasks with a fixed time (e.g. meds at 09:00) are placed at exactly that time. Flexible tasks fill the earliest free gap at or after their preferred time of day (morning, afternoon or evening). *(`Scheduler.assign_time_slots()`)*
- **Explained decisions:** every scheduled task says why it got its slot ("fixed at 09:00", "high priority, preferred morning"). Every skipped task says why it was left out ("not enough time: needs 90 min, 30 min left"). *(`Scheduler.explain_choice()`)*

**Organizing tasks**
- **Sorting by time:** lists tasks in the order they happen. Fixed times come first in clock order, then flexible tasks from morning to evening, with priority breaking ties. *(`Scheduler.sort_by_time()`)*
- **Filtering by pet and status:** shows one pet's tasks, only pending or only completed tasks, or both filters together. *(`Owner.filter_tasks()`)*

**Recurring care**
- **Daily and weekly recurrence:** marking a daily task complete creates the next one, due tomorrow (`+ timedelta(days=1)`). Weekly tasks return in 7 days, and "once" tasks don't repeat. Dates roll over month ends, year ends and leap days correctly. *(`Scheduler.mark_task_complete()`, `Task.next_occurrence()`)*
- **Due and overdue tracking:** a task isn't scheduled before its due date. An overdue task stays on the list instead of being silently dropped. *(`Task.is_due_today()`)*
- **Completion history:** completed tasks are kept and can be shown with the "Completed" filter. Completing the same task twice is blocked, so a double-click can't create duplicate future tasks. *(`Pet.complete_task()`)*

**Conflict handling**
- **Conflict detection:** finds tasks whose time slots overlap, not just ones with the same start time. A 20-minute task at 09:00 clashes with one at 09:10, but back-to-back tasks don't. Tasks are sorted by start time first, so the check can stop early. *(`Scheduler.detect_conflicts()`)*
- **Conflict warnings:** each clash becomes a plain-language warning instead of an error. It says whether one pet is double-booked or the owner would need to be in two places at once, and by how many minutes. *(`Scheduler.conflict_warnings()`)*
- **Fix suggestions:** for each clash, recommends moving the lower-priority task, so medication stays put, to the next free time that fits it. *(`Scheduler.suggest_fix()`)*

**Input checks**
- Frequencies like `"Daily"` or `" weekly "` are accepted as `daily` and `weekly`, and typos like `"monthly"` are rejected. Duplicate pet names and unknown task fields are also rejected. *(`Task._clean_frequency()`, `Owner.add_pet()`, `Task.update()`)*

See [Smarter Scheduling](#-smarter-scheduling) for how each algorithm works, with examples.

## 🛠️ Implementation Summary

The scheduling logic lives in `pawpal_system.py` and is built from four classes:

- **`Task`**: a single care activity (title, description, duration, priority, frequency, completion status). A task can have a fixed `scheduled_time` (e.g. meds at 09:00) or a flexible `preferred_time` of day. Each task is one occurrence: completing a daily or weekly task creates the next occurrence with a `due_date` one or seven days later (`frequency="once"` tasks don't repeat).
- **`Pet`**: a pet's details plus its list of tasks. Adding a task tags it with the pet's name so the plan can show whose task it is. `complete_task()` marks a task done and adds its next occurrence; `Scheduler.mark_task_complete(task)` does the same without the caller having to look up the pet.
- **`Owner`**: the person, their available minutes and day window (default 08:00–20:00), and their pets. `get_all_tasks()` gathers every pet's tasks into one list, and `filter_tasks()` narrows it by pet and/or completion status.
- **`Scheduler`**: the planner. It reads tasks from `Owner.get_all_tasks()`, so it works across all pets, then builds the day in three steps:
  1. **Sort** by priority (high first), then by shorter duration.
  2. **Filter** out tasks already done for the period, and anything that no longer fits in the owner's time budget.
  3. **Assign slots**: fixed-time tasks go at their exact time; flexible tasks fill the earliest free gap at or after their preferred time.

  Every skipped task is recorded with a reason, `explain_choice()` describes why any task was scheduled or skipped, `detect_conflicts()` finds overlapping fixed-time tasks, and `conflict_warnings()` turns them into readable warnings. `sort_by_time()` orders tasks by time of day for display.

`main.py` builds a sample owner with two pets and prints today's schedule, and `tests/test_pawpal.py` covers the key behaviors. The Streamlit UI in `app.py` uses these classes for everything: adding pets and tasks, filtering and sorting the task list, marking tasks done, and generating the plan.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
$ python main.py
All tasks, in the order they were added
------------------------------------------------------------
evening    Mochi  Evening walk     medium  pending
09:00      Mochi  Heartworm meds   high    pending
afternoon  Mochi  Puzzle feeder    low     pending
morning    Mochi  Morning walk     high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
18:00      Luna   Laser play       medium  pending
any        Luna   Full grooming    low     pending
08:00      Luna   Breakfast        medium  pending

All tasks, sorted by time (Scheduler.sort_by_time)
------------------------------------------------------------
08:00      Luna   Breakfast        medium  pending
09:00      Mochi  Heartworm meds   high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
18:00      Luna   Laser play       medium  pending
morning    Mochi  Morning walk     high    pending
afternoon  Mochi  Puzzle feeder    low     pending
evening    Mochi  Evening walk     medium  pending
any        Luna   Full grooming    low     pending

Luna's tasks only (filter_tasks(pet_name='Luna'))
------------------------------------------------------------
18:00      Luna   Laser play       medium  pending
any        Luna   Full grooming    low     pending
08:00      Luna   Breakfast        medium  pending

Marked 'Morning walk' (Mochi) complete; next one due 2026-10-19

Marked 'Breakfast' (Luna) complete; next one due 2026-10-19

Completed tasks (filter_tasks(completed=True))
------------------------------------------------------------
morning    Mochi  Morning walk     high    done 2026-10-18
08:00      Luna   Breakfast        medium  done 2026-10-18

Mochi's pending tasks, sorted by time (filter + sort combined)
------------------------------------------------------------
09:00      Mochi  Heartworm meds   high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
morning    Mochi  Morning walk     high    pending
afternoon  Mochi  Puzzle feeder    low     pending
evening    Mochi  Evening walk     medium  pending

Today's Schedule for Jordan
============================================================
09:00-09:05  Mochi  Heartworm meds   [high]    fixed at 09:00
09:00-09:05  Mochi  Ear drops        [high]    fixed at 09:00
12:00-12:15  Mochi  Puzzle feeder    [low]     low priority, preferred afternoon
17:00-17:30  Mochi  Evening walk     [medium]  medium priority, preferred evening
18:00-18:15  Luna   Laser play       [medium]  fixed at 18:00
18:00-18:20  Mochi  Vet call         [medium]  fixed at 18:00

Skipped
------------------------------------------------------------
Mochi  Morning walk     not due until 2026-10-19
Luna   Breakfast        not due until 2026-10-19
Luna   Full grooming    not enough time: needs 90 min, 30 min left

Conflict check
------------------------------------------------------------
WARNING: Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min
  -> Suggestion: move Ear drops to 09:05
WARNING: Different pets: Laser play (Luna) 18:00-18:15 overlaps Vet call (Mochi) 18:00-18:20 by 15 min
  -> Suggestion: move Vet call to 18:15
```

## 🧪 Testing PawPal+

### Run the tests

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pytest
```

Useful variations: `python -m pytest -v` lists every test by name, and `python -m pytest -k conflict` runs only the tests with "conflict" in the name.

### What the tests cover

The 48 tests in `tests/test_pawpal.py` check the scheduling logic in `pawpal_system.py` directly, without starting the UI:

- **Sorting:** tasks come back in chronological order (07:05 → 09:05 → 09:30 → 12:30 → 18:00), with flexible tasks after them in morning → afternoon → evening order.
- **Recurring tasks:** completing a daily task creates a new one due the next day, and weekly tasks come back in 7 days. "Once" tasks don't repeat. Dates roll over month ends, year ends and leap days correctly.
- **Conflict detection:** tasks at the exact same time or with overlapping time slots are flagged, for the same pet or for different pets. Back-to-back tasks are not flagged, nothing crashes when there's no plan yet, and the suggested fix moves the lower-priority task to a free time.
- **Filtering:** tasks can be listed by pet, by done/pending status, or both.
- **Planning:** higher priority wins when time is short, fixed-time tasks keep their exact time, flexible tasks never overlap them, and every skipped task gets a reason.
- **Bad input:** duplicate pet names, unknown task fields, unknown frequencies, and completing a task twice are all rejected.

### Sample test run

```
=================== test session starts ====================
platform darwin -- Python 3.12.6, pytest-9.1.1, pluggy-1.7.0
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 44 items

tests/test_pawpal.py ............................... [ 70%]
.............                                        [100%]

==================== 44 passed in 0.04s ====================
```

### Confidence level: ★★★★☆ (4/5)

All 48 tests pass, and each core feature is tested on normal cases and on edge cases such as exact ties, back-to-back times, calendar rollovers and bad input. The `main.py` demo gives the same results the tests expect.

It isn't 5 stars because of a few known gaps:

- A "morning" preference sets the earliest start, not a deadline, so on a busy day a morning task can end up in the evening.
- Conflicts are only checked between tasks that made it into the plan.
- The Streamlit UI in `app.py` has no automated tests. It was only checked by hand.

## 📐 Smarter Scheduling

Beyond building the day's plan, PawPal+ can sort tasks by time, filter them by pet or status, catch scheduling conflicts, and bring recurring tasks back automatically. All of this logic lives in `pawpal_system.py`. `app.py` and `main.py` only call it.

| Feature | Method(s) | In one sentence |
|---------|-----------|-----------------|
| [Sorting](#sorting) | `Scheduler.sort_by_time()`, `Scheduler.sort_tasks()` | Orders tasks by time of day for display, or by priority for planning. |
| [Filtering](#filtering) | `Owner.filter_tasks()`, `Scheduler.filter_tasks()` | Narrows tasks by pet and/or completion status; drops tasks that aren't due or don't fit. |
| [Conflict detection](#conflict-detection) | `Scheduler.detect_conflicts()`, `Scheduler.conflict_warnings()`, `Scheduler.suggest_fix()` | Finds overlapping time slots, returns warnings instead of crashing, and suggests which task to move and when. |
| [Recurring tasks](#recurring-tasks) | `Scheduler.mark_task_complete()`, `Pet.complete_task()`, `Task.next_occurrence()`, `Task.is_due_today()` | Completing a daily or weekly task creates its next occurrence. |

### Sorting

**`Scheduler.sort_by_time(tasks)`** puts tasks in the order they happen during the day. It returns a new list and leaves the original unchanged. The sort key is a tuple, compared left to right:

1. Fixed-time tasks come before flexible ones.
2. Fixed-time tasks are ordered by clock time (`scheduled_time`).
3. Flexible tasks are ordered by preferred time of day: morning, then afternoon, then evening, then any.
4. Ties go to the higher-priority task.

`scheduled_time` is stored as a `datetime.time`, not an `"HH:MM"` string, so 9:30 always sorts before 18:00 and no string parsing is needed.

**`Scheduler.sort_tasks(tasks)`** is the other ordering, used when building the plan. It sorts by priority (high first), then shorter duration, then preferred time, so the most important tasks claim the available time first.

Tasks added out of order (`python main.py`):

```
All tasks, sorted by time (Scheduler.sort_by_time)
08:00      Luna   Breakfast        medium  pending
09:00      Mochi  Heartworm meds   high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
18:00      Luna   Laser play       medium  pending
morning    Mochi  Morning walk     high    pending
afternoon  Mochi  Puzzle feeder    low     pending
evening    Mochi  Evening walk     medium  pending
any        Luna   Full grooming    low     pending
```

**In the app:** the task table is always shown in `sort_by_time()` order.

### Filtering

**`Owner.filter_tasks(pet_name=None, completed=None)`** returns the tasks that match both filters. Leaving a filter as `None` means "any":

```python
owner.filter_tasks(pet_name="Mochi")                   # all of Mochi's tasks
owner.filter_tasks(completed=True)                     # everything already done
owner.filter_tasks(pet_name="Mochi", completed=False)  # Mochi's to-do list
```

An unknown pet name returns an empty list rather than an error. You can combine it with sorting: `scheduler.sort_by_time(owner.filter_tasks(pet_name="Mochi", completed=False))`.

**`Scheduler.filter_tasks(tasks, day)`** is the filter used while planning. It works through the priority-sorted tasks and keeps each one that is due on `day` and still fits in the owner's remaining minutes. Every task it drops goes into `scheduler.skipped` with a reason:

```
Skipped
Mochi  Morning walk     not due until 2026-10-19
Luna   Breakfast        not due until 2026-10-19
Luna   Full grooming    not enough time: needs 90 min, 30 min left
```

`generate_plan()` uses `Owner.filter_tasks(completed=False)` first, so completed tasks don't clutter the skipped list. If a task passes the time budget but then can't be placed (its fixed time is outside the owner's day, or there's no free gap), `generate_plan()` removes it and recomputes the budget, so its minutes go to the next task that fits.

**In the app:** use the **Pet** ("All pets" or one pet) and **Status** (Pending / Completed / All) dropdowns above the task table.

### Conflict detection

**`Scheduler.detect_conflicts()`** returns `(task, task)` pairs from the current plan whose time slots overlap. It works in three steps:

1. Sort plan entries by start time.
2. For each entry, compare it with the entries after it. Because those start no earlier, entry `b` overlaps entry `a` exactly when `b.start < a.end`.
3. Stop as soon as a later entry starts at or after `a.end`. Every entry after that starts even later, so none of them can overlap either.

This avoids comparing every possible pair, so it costs O(n log n + k) for k conflicts. It checks **overlapping durations**, not just matching start times: a 09:00–09:20 task conflicts with one at 09:10. Back-to-back tasks (09:00–09:30, then 09:30) are not a conflict.

**`Scheduler.conflict_warnings()`** turns each pair into a readable message, labelled by whether one pet is double-booked or the owner would need to be in two places at once:

```
WARNING: Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min
WARNING: Different pets: Laser play (Luna) 18:00-18:15 overlaps Vet call (Mochi) 18:00-18:20 by 15 min
```

**This approach is deliberately lightweight.** Conflicts never raise an exception or block the plan. Both tasks keep their requested times and the owner decides which to move, because a fixed time (a vet appointment, medication) usually matters for a reason outside the app. Only fixed-time tasks can conflict, since flexible tasks are always placed in free gaps. See `reflection.md` section 2b for the full tradeoff.

**`Scheduler.suggest_fix(a, b)`** recommends a fix for a conflicting pair. The lower-priority task is the one to move (on a tie, the later one), so medication stays put. The suggested time is the first free gap at or after its current time that fits its whole duration. If nothing fits before the end of the day, it searches again from the start of the day, and it returns `None` if no gap is long enough.

**In the app:** a "Conflicts" counter sits above the schedule. Each conflict gets its own yellow warning that says in plain words what clashes ("Mochi has two tasks at once" or "You can't be in two places at once") and suggests a fix ("move **Ear drops** (medium priority) to **09:05**"). The clashing rows in the schedule table are marked ⚠️. When there are no conflicts, a green "No time conflicts" message appears instead.

### Recurring tasks

Each `Task` is one occurrence. Completing a recurring task keeps it as history and creates the next occurrence.

- **`Scheduler.mark_task_complete(task, day=None)`** is the entry point. It finds the task's pet and calls `Pet.complete_task()`, and it returns the new task (or `None`).
- **`Pet.complete_task(task_id, day=None)`** marks the task done, then adds the next occurrence to the same pet. It refuses to complete a task twice, so double-clicking can't create duplicate occurrences.
- **`Task.next_occurrence()`** builds the copy. It sets `due_date = completion day + timedelta(days=1)` for `"daily"` tasks and `+ timedelta(days=7)` for `"weekly"` ones, and returns `None` for `"once"`. Adding a `timedelta` handles month ends, year ends and leap days (Oct 31 → Nov 1, Feb 28 2028 → Feb 29).
- **`Task.is_due_today(day)`** returns False for completed tasks and for tasks whose `due_date` is still in the future. Overdue tasks still count as due, so they aren't silently dropped.

Frequency is normalized when a task is created or edited, so `"Daily"` and `" weekly "` work. Unknown values like `"monthly"` raise a `ValueError` instead of silently never repeating.

```
Marked 'Morning walk' (Mochi) complete; next one due 2026-10-19
Marked 'Breakfast' (Luna) complete; next one due 2026-10-19
```

**In the app:** pick a task under **Mark a task done** and click **Mark complete**. The confirmation shows the next due date, and the new occurrence appears in the task table.

> Call `Scheduler.mark_task_complete()` (or `Pet.complete_task()`), not `Task.mark_complete()`. A `Task` doesn't know which pet it belongs to, so `Task.mark_complete()` marks it done without creating the next occurrence.

### Tested behaviors

`tests/test_pawpal.py` covers each feature (48 tests):

- **Sorting:** fixed-time tasks come back in chronological order, minutes included (`test_sort_by_time_returns_tasks_in_chronological_order`); fixed times come first in clock order, then flexible tasks by preferred time (`test_sort_by_time_puts_fixed_times_first_then_preferred_time`); the plan is ordered by start time (`test_plan_is_sorted_by_start_time`).
- **Filtering:** by pet, by status, by both, with no filters, and with an unknown pet (`test_filter_tasks_by_pet_and_status`).
- **Conflicts:**
  - two tasks at the exact same time, for the same pet and for different pets
  - overlapping tasks for different pets and for the same pet
  - every overlapping pair reported when one long task overlaps several
  - back-to-back tasks not flagged
  - no crash before a plan exists
  - `suggest_fix()` moves the lower-priority task (the later one on a tie), searches earlier in the day when nothing fits later, and returns `None` when no gap is long enough
- **Recurring tasks:**
  - daily tasks come back +1 day, weekly +7, and "once" tasks don't repeat
  - month, year and leap-day rollover
  - completing a task twice is rejected
  - next occurrences aren't scheduled before their due date
  - frequency normalization and rejection of unknown values

## 📸 Demo Walkthrough

Start the app with `streamlit run app.py`. Everything happens on one page, in four sections from top to bottom.

### Main UI features

| Section | What you can do |
|---------|-----------------|
| **Owner** | Set your name, how many **minutes** you have for pet care today, and when your **day starts and ends** (default 08:00–20:00). The scheduler never plans more than either limit allows. |
| **Add a pet** | Add a pet with a name, species (dog / cat / other) and age. Each pet name must be unique. |
| **Add a task** | Pick a pet, then give the task a title, duration and priority (low / medium / high). Optionally, set a **fixed time** (e.g. meds at 09:00) *or* a **preferred time of day** (morning / afternoon / evening), and choose whether it repeats **daily**, **weekly** or **once**. |
| **Tasks list** | See every task in time-of-day order. Use the **Pet** and **Status** (Pending / Completed / All) dropdowns to filter it. Use **Mark a task done** to complete a task; repeating tasks automatically come back on their next due date. |
| **Build schedule** | Click **Generate schedule** to see today's plan, with counters for tasks scheduled, minutes used, conflicts, and tasks not scheduled. Conflict warnings come with suggested fixes. The schedule table says why each task got its slot, and a "Not scheduled today" table says why anything was left out. The schedule stays on screen and updates as you add or complete tasks. |

### Example workflow

1. **Set up the owner.** Leave the name as *Jordan*, with **120** minutes available and a day running 08:00–20:00.
2. **Add two pets.** Add *Mochi* (dog), then *Luna* (cat). A green "Added Luna." message appears, and the line under the form reads "Your pets: **Mochi** (dog), **Luna** (cat)".
3. **Add four tasks:**
   - Mochi, *Morning walk*, 30 min, high priority, preferred time **morning**
   - Mochi, *Heartworm meds*, 5 min, high priority, fixed time **09:00**
   - Luna, *Vet call*, 20 min, medium priority, fixed time **09:00**
   - Luna, *Full grooming*, 90 min, low priority, any time

   The task list sorts them by time of day, not by the order you added them. The two 09:00 tasks come first, then the morning walk, then grooming. The caption reads "Showing 4 of 4 tasks, sorted by time of day."
4. **Generate the schedule.** The counters show **Scheduled 3 · Minutes used 55 / 120 · Conflicts 1 · Not scheduled 1**, and a yellow warning appears:

   > ⚠️ **You can't be in two places at once:** Heartworm meds for Mochi (09:00–09:05) and Vet call for Luna (09:00–09:20).
   >
   > 💡 Suggestion: move **Vet call** (medium priority) to **09:05**, the next free time.

   | Time | Pet | Task | Priority | Why this slot |
   |------|-----|------|----------|---------------|
   | 08:00–08:30 | Mochi | Morning walk | 🔴 High | High priority, preferred morning |
   | 09:00–09:05 | Mochi | ⚠️ Heartworm meds | 🔴 High | Fixed at 09:00 |
   | 09:00–09:20 | Luna | ⚠️ Vet call | 🟡 Medium | Fixed at 09:00 |

   Under "Not scheduled today": *Full grooming — Not enough time: needs 90 min, 65 min left.*
5. **Complete a task.** Under **Mark a task done**, pick *Morning walk (Mochi)* and click **Mark complete**. The app confirms "Marked 'Morning walk' done for Mochi. Next one is due Oct 19." The schedule updates on its own:
   - The walk moves to "Not scheduled today" with the reason *Not due until 2026-10-19*.
   - The 30 minutes it freed up are enough for *Full grooming*, which now fits at **09:20–10:50** (Minutes used 115 / 120).
6. **Review history.** Set the **Status** filter to *Completed* to see the finished walk ("✅ Done Oct 18"). Set it to *Pending* to see tomorrow's walk, due Oct 19.

### Key Scheduler behaviors shown

- **Sorting by time** (`Scheduler.sort_by_time()`): the task list in step 3 puts fixed times first in clock order, then flexible tasks from morning to evening, regardless of the order they were added.
- **Priority under a time limit** (`Scheduler.sort_tasks()`, `Scheduler.filter_tasks()`): in step 4, the high-priority tasks are placed first, and the 90-minute low-priority grooming is left out with the exact reason why.
- **Smart slot placement** (`Scheduler.assign_time_slots()`): fixed-time tasks stay at their exact time, and the flexible walk takes the first free morning gap (08:00), before the 09:00 tasks.
- **Conflict warnings and fixes** (`Scheduler.detect_conflicts()`, `conflict_warnings()`, `suggest_fix()`): the overlapping 09:00 tasks produce a plain-language warning, ⚠️ markers in the table, and a suggestion to move the lower-priority task instead of an error. Same-pet clashes say "Mochi has two tasks at once" instead.
- **Daily recurrence** (`Scheduler.mark_task_complete()`, `Task.next_occurrence()`): completing the walk in step 5 creates tomorrow's walk, which stays out of today's plan until it's due.
- **Re-planning with freed time** (`Scheduler.generate_plan()`): the schedule rebuilds after every change, so time freed by completing the walk goes straight to the next task that fits.
- **Filtering** (`Owner.filter_tasks()`): step 6 switches between completed and pending tasks.

### Sample CLI output

`main.py` runs a similar scenario without the UI. It adds tasks out of order, sorts and filters them, marks two tasks complete, builds the schedule, and checks for conflicts (one same-pet clash, one between different pets):

```
$ python main.py
All tasks, in the order they were added
------------------------------------------------------------
evening    Mochi  Evening walk     medium  pending
09:00      Mochi  Heartworm meds   high    pending
afternoon  Mochi  Puzzle feeder    low     pending
morning    Mochi  Morning walk     high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
18:00      Luna   Laser play       medium  pending
any        Luna   Full grooming    low     pending
08:00      Luna   Breakfast        medium  pending

All tasks, sorted by time (Scheduler.sort_by_time)
------------------------------------------------------------
08:00      Luna   Breakfast        medium  pending
09:00      Mochi  Heartworm meds   high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
18:00      Luna   Laser play       medium  pending
morning    Mochi  Morning walk     high    pending
afternoon  Mochi  Puzzle feeder    low     pending
evening    Mochi  Evening walk     medium  pending
any        Luna   Full grooming    low     pending

Luna's tasks only (filter_tasks(pet_name='Luna'))
------------------------------------------------------------
18:00      Luna   Laser play       medium  pending
any        Luna   Full grooming    low     pending
08:00      Luna   Breakfast        medium  pending

Marked 'Morning walk' (Mochi) complete; next one due 2026-10-19

Marked 'Breakfast' (Luna) complete; next one due 2026-10-19

Completed tasks (filter_tasks(completed=True))
------------------------------------------------------------
morning    Mochi  Morning walk     high    done 2026-10-18
08:00      Luna   Breakfast        medium  done 2026-10-18

Mochi's pending tasks, sorted by time (filter + sort combined)
------------------------------------------------------------
09:00      Mochi  Heartworm meds   high    pending
09:00      Mochi  Ear drops        high    pending
18:00      Mochi  Vet call         medium  pending
morning    Mochi  Morning walk     high    pending
afternoon  Mochi  Puzzle feeder    low     pending
evening    Mochi  Evening walk     medium  pending

Today's Schedule for Jordan
============================================================
09:00-09:05  Mochi  Heartworm meds   [high]    fixed at 09:00
09:00-09:05  Mochi  Ear drops        [high]    fixed at 09:00
12:00-12:15  Mochi  Puzzle feeder    [low]     low priority, preferred afternoon
17:00-17:30  Mochi  Evening walk     [medium]  medium priority, preferred evening
18:00-18:15  Luna   Laser play       [medium]  fixed at 18:00
18:00-18:20  Mochi  Vet call         [medium]  fixed at 18:00

Skipped
------------------------------------------------------------
Mochi  Morning walk     not due until 2026-10-19
Luna   Breakfast        not due until 2026-10-19
Luna   Full grooming    not enough time: needs 90 min, 30 min left

Conflict check
------------------------------------------------------------
WARNING: Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min
  -> Suggestion: move Ear drops to 09:05
WARNING: Different pets: Laser play (Luna) 18:00-18:15 overlaps Vet call (Mochi) 18:00-18:20 by 15 min
  -> Suggestion: move Vet call to 18:15
```
