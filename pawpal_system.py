"""PawPal+ logic layer.

Backend classes for the pet care planner (Owner, Pet, Task, Scheduler).
The Streamlit UI in app.py imports from this module; keep UI code out of here.
"""

from dataclasses import dataclass, field, fields, replace
from datetime import date, time, timedelta
from typing import Optional
from uuid import uuid4

PRIORITY_VALUES = {"high": 3, "medium": 2, "low": 1}

# Earliest start (minutes after midnight) for each preferred time of day.
PREFERRED_START = {"morning": 6 * 60, "afternoon": 12 * 60, "evening": 17 * 60}
PREFERRED_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}
# Days until a recurring task comes back; "once" tasks are not listed and never repeat.
FREQUENCY_DAYS = {"daily": 1, "weekly": 7}
FREQUENCIES = {*FREQUENCY_DAYS, "once"}


def _to_minutes(t: time) -> int:
    """Convert a time of day to minutes after midnight."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes after midnight back to a time of day."""
    return time(minutes // 60, minutes % 60)


def _new_id() -> str:
    """Return a short random task id."""
    return uuid4().hex[:8]


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, etc.)."""

    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    description: str = ""
    category: str = "other"  # walk, feeding, meds, enrichment, grooming, other
    scheduled_time: Optional[time] = None  # fixed start time (e.g. meds at 09:00); None = flexible
    preferred_time: Optional[str] = None  # "morning" | "afternoon" | "evening"
    frequency: str = "daily"  # "daily" | "weekly" | "once"
    completed: bool = False
    last_completed: Optional[date] = None  # the day this occurrence was done
    due_date: Optional[date] = None  # earliest day this occurrence can be scheduled; None = now
    pet_name: str = ""  # set by Pet.add_task so the plan knows whose task it is
    task_id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        """Normalize the frequency so "Daily" or " weekly " still repeat, and reject unknown ones."""
        self.frequency = self._clean_frequency(self.frequency)

    @staticmethod
    def _clean_frequency(value: str) -> str:
        """Return `value` trimmed and lowercased, or raise ValueError if it isn't a known frequency.

        Args:
            value: A frequency as typed by the user, e.g. "Daily" or " weekly ".

        Returns:
            The canonical spelling: "daily", "weekly", or "once".

        Raises:
            ValueError: If the cleaned value isn't in FREQUENCIES (e.g. "monthly"), so a typo
                fails loudly instead of creating a task that silently never repeats.
        """
        cleaned = str(value).strip().lower()
        if cleaned not in FREQUENCIES:
            raise ValueError(f"Unknown frequency {value!r}; use one of: {', '.join(sorted(FREQUENCIES))}")
        return cleaned

    def mark_complete(self, day: Optional[date] = None) -> None:
        """Mark this task as done on `day` (defaults to today)."""
        self.completed = True
        self.last_completed = day or date.today()

    def priority_value(self) -> int:
        """Return a numeric priority for sorting (high=3, medium=2, low=1)."""
        return PRIORITY_VALUES.get(self.priority.lower(), 0)

    def is_due_today(self, day: date) -> bool:
        """Return True if this task is still open and due on (or before) `day`.

        A completed occurrence is never due again; its follow-up is a separate Task created by
        next_occurrence(). A task with no due_date is due immediately, and an overdue task
        (due_date earlier than `day`) still counts as due so it isn't silently dropped.

        Args:
            day: The day being planned.

        Returns:
            True if the task should be considered for that day's plan.
        """
        if self.completed:
            return False
        return self.due_date is None or self.due_date <= day

    def next_occurrence(self) -> Optional["Task"]:
        """Return a fresh copy due one period after this task was completed, or None if it doesn't repeat.

        A daily task completed today is next due today + 1 day; a weekly one, today + 7 days.
        Adding a timedelta to a date rolls over month/year ends and leap days correctly
        (Oct 31 -> Nov 1, Dec 31 -> Jan 1, Feb 28 2028 -> Feb 29).

        The copy keeps every detail (title, duration, priority, times, pet) but gets a new
        task_id, completed=False, and no last_completed. This method only builds the copy;
        Pet.complete_task() is what adds it to the pet.

        Returns:
            The next occurrence, or None if the task is "once" or hasn't been completed yet.

        Example:
            >>> walk = Task("Walk", 30, frequency="daily")
            >>> walk.mark_complete(date(2026, 10, 31))
            >>> walk.next_occurrence().due_date
            datetime.date(2026, 11, 1)
        """
        interval = FREQUENCY_DAYS.get(self.frequency)
        if interval is None or self.last_completed is None:
            return None
        return replace(
            self,
            completed=False,
            last_completed=None,
            due_date=self.last_completed + timedelta(days=interval),
            task_id=_new_id(),
        )

    def update(self, changes: dict) -> None:
        """Update this task's fields from a dict of new values."""
        allowed = {f.name for f in fields(self)} - {"task_id"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unknown task field(s): {', '.join(sorted(unknown))}")
        if "frequency" in changes:
            changes = {**changes, "frequency": self._clean_frequency(changes["frequency"])}
        for name, value in changes.items():
            setattr(self, name, value)


@dataclass
class Pet:
    """A pet and the care tasks it needs."""

    name: str
    species: str  # "dog" | "cat" | "other"
    age: Optional[int] = None
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet and tag it with this pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def edit_task(self, task_id: str, changes: dict) -> None:
        """Update the task with the given id."""
        self._find_task(task_id).update(changes)

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id."""
        self.tasks.remove(self._find_task(task_id))

    def complete_task(self, task_id: str, day: Optional[date] = None) -> Optional[Task]:
        """Mark a task done and, if it repeats, add its next occurrence. Return that new task (or None).

        The completed task stays in this pet's list as history, so filtering by
        completed=True still shows what was done.

        Args:
            task_id: The id of one of this pet's tasks.
            day: The day it was completed; defaults to today.

        Returns:
            The newly added next occurrence, or None for a "once" task.

        Raises:
            KeyError: If this pet has no task with that id.
            ValueError: If the task is already completed (prevents creating a duplicate
                next occurrence when "Mark complete" is clicked twice).
        """
        task = self._find_task(task_id)
        if task.completed:
            raise ValueError(f"{task.title!r} is already completed")
        task.mark_complete(day)
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming

    def get_tasks(self) -> list[Task]:
        """Return all of this pet's tasks."""
        return list(self.tasks)

    def _find_task(self, task_id: str) -> Task:
        """Return the task with the given id, or raise KeyError if this pet doesn't have it."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(f"{self.name} has no task with id {task_id!r}")


@dataclass
class Owner:
    """The pet owner, their availability, and their pets."""

    name: str
    available_minutes: int = 120
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        self.pets = [p for p in self.pets if p is not pet]

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.get_tasks()]

    def filter_tasks(self, pet_name: Optional[str] = None, completed: Optional[bool] = None) -> list[Task]:
        """Return tasks for one pet and/or with one completion status; None means "any".

        Both filters are optional and combine with AND. Results keep the order of
        get_all_tasks() (pet by pet, in the order tasks were added); pass them to
        Scheduler.sort_by_time() for time-of-day order.

        Args:
            pet_name: Only include this pet's tasks. None includes every pet.
            completed: True for done tasks, False for pending ones, None for both.

        Returns:
            A new list of matching tasks (empty if nothing matches, e.g. an unknown pet name).

        Example:
            owner.filter_tasks(pet_name="Mochi", completed=False)  # Mochi's to-do list
        """
        return [
            task
            for task in self.get_all_tasks()
            if (pet_name is None or task.pet_name == pet_name)
            and (completed is None or task.completed == completed)
        ]

    def set_availability(self, minutes: int, start: time, end: time) -> None:
        """Set how much time the owner has today and their day window."""
        if minutes < 0:
            raise ValueError("Available minutes can't be negative")
        if start >= end:
            raise ValueError("Day start must be before day end")
        self.available_minutes = minutes
        self.day_start = start
        self.day_end = end


class Scheduler:
    """Builds and explains a daily care plan for an owner's pets."""

    def __init__(self, owner: Owner):
        """Create a scheduler for `owner` with an empty plan and skipped list."""
        # Tasks and available time are read from the owner when a plan is built,
        # so the scheduler never works from a stale copy.
        self.owner = owner
        self.plan: list[dict] = []  # {"task", "pet", "start", "end", "reason"} per scheduled task
        self.skipped: list[tuple[Task, str]] = []  # (task, reason it was left out)

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority (then duration / preferred time)."""
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority_value(),
                t.duration_minutes,
                PREFERRED_ORDER.get(t.preferred_time, 3),
            ),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by time of day: fixed-time tasks by clock time, then flexible ones by preferred time.

        The sort key is a tuple, compared left to right; each part only matters when
        everything before it is equal:
            1. has no fixed time (False < True, so fixed-time tasks come first)
            2. scheduled_time (time.min stands in for None, since None can't be compared)
            3. preferred time of day: morning < afternoon < evening < any
            4. priority, negated so high comes first

        This is for display (what happens when). For deciding what makes it into the
        plan, use sort_tasks(), which orders by priority instead.

        Args:
            tasks: Tasks in any order. The list isn't modified.

        Returns:
            A new sorted list, e.g. 08:00, 09:00, 18:00, then morning, afternoon, evening, any.
        """
        return sorted(
            tasks,
            key=lambda t: (
                t.scheduled_time is None,
                t.scheduled_time or time.min,
                PREFERRED_ORDER.get(t.preferred_time, 3),
                -t.priority_value(),
            ),
        )

    def filter_tasks(self, tasks: list[Task], day: date) -> list[Task]:
        """Keep tasks due on `day` that fit the time available; record the rest in self.skipped."""
        window = _to_minutes(self.owner.day_end) - _to_minutes(self.owner.day_start)
        remaining = min(self.owner.available_minutes, window)
        kept = []
        for task in tasks:
            if task.completed:
                self.skipped.append((task, f"already done (completed {task.last_completed})"))
            elif not task.is_due_today(day):
                self.skipped.append((task, f"not due until {task.due_date}"))
            elif task.duration_minutes > remaining:
                self.skipped.append(
                    (task, f"not enough time: needs {task.duration_minutes} min, {remaining} min left")
                )
            else:
                kept.append(task)
                remaining -= task.duration_minutes
        return kept

    def assign_time_slots(self, tasks: list[Task]) -> list[dict]:
        """Give each chosen task a start and end time within the owner's day."""
        day_start = _to_minutes(self.owner.day_start)
        day_end = _to_minutes(self.owner.day_end)
        slots = []

        # Fixed-time tasks go exactly where they were asked to be.
        flexible = []
        for task in tasks:
            if task.scheduled_time is None:
                flexible.append(task)
                continue
            start = _to_minutes(task.scheduled_time)
            end = start + task.duration_minutes
            if start < day_start or end > day_end:
                self.skipped.append((task, "fixed time falls outside the owner's day"))
                continue
            slots.append(self._entry(task, start, end, f"fixed at {task.scheduled_time:%H:%M}"))

        # Flexible tasks (already in priority order) take the earliest free gap
        # at or after their preferred time of day.
        busy = sorted((_to_minutes(s["start"]), _to_minutes(s["end"])) for s in slots)
        for task in flexible:
            start = max(day_start, PREFERRED_START.get(task.preferred_time or "", day_start))
            for busy_start, busy_end in busy:
                if start < busy_end and busy_start < start + task.duration_minutes:
                    start = busy_end
            end = start + task.duration_minutes
            if end > day_end:
                self.skipped.append((task, "no free slot left before the end of the day"))
                continue
            reason = f"{task.priority} priority"
            if task.preferred_time:
                reason += f", preferred {task.preferred_time}"
            slots.append(self._entry(task, start, end, reason))
            busy = sorted(busy + [(start, end)])

        return sorted(slots, key=lambda s: s["start"])

    def detect_conflicts(self) -> list[tuple]:
        """Return (task, task) pairs from self.plan whose time slots overlap.

        Algorithm (sort, then scan forward with an early stop):
            1. Sort plan entries by start time.
            2. For each entry `a`, look at the entries after it. Because they start no
               earlier than `a`, `b` overlaps `a` exactly when b.start < a.end.
            3. As soon as some `b` starts at or after a.end, stop: every later entry
               starts even later, so none of them can overlap `a` either.

        That makes it O(n log n + k) for k conflicts instead of comparing every pair.
        Overlap means real overlapping durations, not just equal start times: 09:00-09:20
        conflicts with 09:10-09:30. Back-to-back tasks (one ends 09:30, the next starts
        09:30) are not a conflict.

        Returns:
            A list of (earlier task, later task) pairs; empty if there are no conflicts or
            no plan has been generated yet.
        """
        entries = sorted(self.plan, key=lambda e: e["start"])
        conflicts = []
        for i, a in enumerate(entries):
            for b in entries[i + 1 :]:
                if b["start"] >= a["end"]:
                    break  # entries are sorted by start, so no later one can overlap `a` either
                conflicts.append((a["task"], b["task"]))
        return conflicts

    def conflict_warnings(self) -> list[str]:
        """Describe each overlap in self.plan as a readable warning; empty if there are none.

        Lightweight by design: conflicting tasks stay in the plan and nothing is raised.
        The caller decides how to show the warnings (print, st.warning, ...).

        Each warning says whether the clash is for the same pet (one pet booked twice) or
        different pets (the owner can't be in two places), and by how many minutes the
        slots overlap.

        Returns:
            One message per pair from detect_conflicts(), for example:
            "Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min"
            "Different pets: Laser play (Luna) 18:00-18:15 overlaps Vet call (Mochi) 18:00-18:20 by 15 min"
        """
        slots = {id(e["task"]): e for e in self.plan}
        warnings = []
        for a, b in self.detect_conflicts():
            sa, sb = slots[id(a)], slots[id(b)]
            overlap = _to_minutes(min(sa["end"], sb["end"])) - _to_minutes(max(sa["start"], sb["start"]))
            span_a = f"{sa['start']:%H:%M}-{sa['end']:%H:%M}"
            span_b = f"{sb['start']:%H:%M}-{sb['end']:%H:%M}"
            if a.pet_name == b.pet_name:
                warnings.append(
                    f"Same pet ({a.pet_name}): {a.title} {span_a} overlaps {b.title} {span_b} by {overlap} min"
                )
            else:
                warnings.append(
                    f"Different pets: {a.title} ({a.pet_name}) {span_a} overlaps "
                    f"{b.title} ({b.pet_name}) {span_b} by {overlap} min"
                )
        return warnings

    def mark_task_complete(self, task: Task, day: Optional[date] = None) -> Optional[Task]:
        """Complete `task` for its pet; daily/weekly tasks get a new instance for the next occurrence.

        Finds the pet through task.pet_name and hands off to Pet.complete_task(), so callers
        (the UI, main.py) don't have to look the pet up themselves. Use this rather than
        Task.mark_complete(), which only marks the task done and can't add the next instance.

        Args:
            task: A task belonging to one of this owner's pets.
            day: The day it was completed; defaults to today. The next daily occurrence is
                due day + 1, a weekly one day + 7.

        Returns:
            The new next-occurrence task, or None for a "once" task.

        Raises:
            KeyError: If the task isn't attached to one of the owner's pets.
            ValueError: If the task is already completed.
        """
        pet = next((p for p in self.owner.pets if p.name == task.pet_name), None)
        if pet is None:
            raise KeyError(f"{self.owner.name} has no pet named {task.pet_name!r}")
        return pet.complete_task(task.task_id, day)

    def generate_plan(self, day: Optional[date] = None) -> list[dict]:
        """Run sort -> filter -> assign slots on the owner's tasks; store and return self.plan.

        filter_tasks() charges each task's minutes to the time budget before slots are
        assigned, so a task that then can't be placed (fixed time outside the owner's day,
        or no free gap) would waste minutes another task could have used. When that
        happens, the unplaceable tasks are set aside and the budget is recomputed without
        them. Each round removes at least one task, so the loop always ends.
        """
        day = day or date.today()
        candidates = self.sort_tasks(self.owner.filter_tasks(completed=False))  # finished ones are history
        unplaceable: list[tuple[Task, str]] = []
        while True:
            self.plan, self.skipped = [], []
            chosen = self.filter_tasks(candidates, day)
            budget_skips = len(self.skipped)
            self.plan = self.assign_time_slots(chosen)
            dropped = self.skipped[budget_skips:]  # tasks that passed the budget but couldn't be placed
            if not dropped:
                break
            unplaceable += dropped
            dropped_ids = {id(task) for task, _ in dropped}
            candidates = [t for t in candidates if id(t) not in dropped_ids]
        self.skipped += unplaceable
        return self.plan

    def explain_choice(self, task: Task) -> str:
        """Explain why a task was scheduled or skipped, using self.plan and self.skipped."""
        for entry in self.plan:
            if entry["task"] is task:
                return (
                    f"{task.title} ({entry['pet']}) is scheduled "
                    f"{entry['start']:%H:%M}-{entry['end']:%H:%M}: {entry['reason']}."
                )
        for skipped_task, reason in self.skipped:
            if skipped_task is task:
                return f"{task.title} ({task.pet_name}) was skipped: {reason}."
        if task.completed:
            return f"{task.title} ({task.pet_name}) is already done (completed {task.last_completed})."
        return f"{task.title} is not in the current plan. Generate a plan first."

    @staticmethod
    def _entry(task: Task, start: int, end: int, reason: str) -> dict:
        """Build one plan entry from a task, start/end minutes after midnight, and a reason."""
        return {
            "task": task,
            "pet": task.pet_name,
            "start": _to_time(start),
            "end": _to_time(end),
            "reason": reason,
        }
