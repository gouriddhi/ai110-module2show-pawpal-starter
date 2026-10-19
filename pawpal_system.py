"""PawPal+ logic layer.

Backend classes for the pet care planner (Owner, Pet, Task, Scheduler).
The Streamlit UI in app.py imports from this module; keep UI code out of here.
"""

from dataclasses import dataclass, field, fields
from datetime import date, time
from typing import Optional
from uuid import uuid4

PRIORITY_VALUES = {"high": 3, "medium": 2, "low": 1}

# Earliest start (minutes after midnight) for each preferred time of day.
PREFERRED_START = {"morning": 6 * 60, "afternoon": 12 * 60, "evening": 17 * 60}
PREFERRED_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}


def _to_minutes(t: time) -> int:
    """Convert a time of day to minutes after midnight."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes after midnight back to a time of day."""
    return time(minutes // 60, minutes % 60)


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
    frequency: str = "daily"  # "daily" | "weekly"
    completed: bool = False
    last_completed: Optional[date] = None  # lets recurring tasks reset each day/week
    pet_name: str = ""  # set by Pet.add_task so the plan knows whose task it is
    task_id: str = field(default_factory=lambda: uuid4().hex[:8])

    def mark_complete(self, day: Optional[date] = None) -> None:
        """Mark this task as done on `day` (defaults to today)."""
        self.completed = True
        self.last_completed = day or date.today()

    def priority_value(self) -> int:
        """Return a numeric priority for sorting (high=3, medium=2, low=1)."""
        return PRIORITY_VALUES.get(self.priority.lower(), 0)

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should be scheduled on the given day."""
        if self.last_completed is None:
            return True
        days_since = (day - self.last_completed).days
        if self.frequency == "weekly":
            return days_since >= 7
        return days_since >= 1

    def update(self, changes: dict) -> None:
        """Update this task's fields from a dict of new values."""
        allowed = {f.name for f in fields(self)} - {"task_id"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unknown task field(s): {', '.join(sorted(unknown))}")
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

    def filter_tasks(self, tasks: list[Task], day: date) -> list[Task]:
        """Keep tasks due on `day` that fit the time available; record the rest in self.skipped."""
        window = _to_minutes(self.owner.day_end) - _to_minutes(self.owner.day_start)
        remaining = min(self.owner.available_minutes, window)
        kept = []
        for task in tasks:
            if not task.is_due_today(day):
                self.skipped.append((task, f"already done (last completed {task.last_completed})"))
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
        """Return pairs of entries in self.plan whose time slots overlap."""
        conflicts = []
        for i, a in enumerate(self.plan):
            for b in self.plan[i + 1 :]:
                if a["start"] < b["end"] and b["start"] < a["end"]:
                    conflicts.append((a["task"], b["task"]))
        return conflicts

    def generate_plan(self, day: Optional[date] = None) -> list[dict]:
        """Run sort -> filter -> assign slots on the owner's tasks; store and return self.plan."""
        day = day or date.today()
        self.plan, self.skipped = [], []
        tasks = self.owner.get_all_tasks()
        chosen = self.filter_tasks(self.sort_tasks(tasks), day)
        self.plan = self.assign_time_slots(chosen)
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
