"""PawPal+ logic layer.

Backend classes for the pet care planner (Owner, Pet, Task, Scheduler).
The Streamlit UI in app.py imports from this module; keep UI code out of here.
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, etc.)."""

    task_id: str
    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    category: str = "other"  # walk, feeding, meds, enrichment, grooming, other
    preferred_time: Optional[str] = None  # "morning" | "afternoon" | "evening"
    frequency: str = "daily"  # "daily" | "weekly"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        raise NotImplementedError

    def priority_value(self) -> int:
        """Return a numeric priority for sorting (high=3, medium=2, low=1)."""
        raise NotImplementedError

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should be scheduled on the given day."""
        raise NotImplementedError

    def update(self, changes: dict) -> None:
        """Update this task's fields from a dict of new values."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the care tasks it needs."""

    name: str
    species: str  # "dog" | "cat" | "other"
    age: Optional[int] = None
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        raise NotImplementedError

    def edit_task(self, task_id: str, changes: dict) -> None:
        """Update the task with the given id."""
        raise NotImplementedError

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id."""
        raise NotImplementedError

    def get_tasks(self) -> list[Task]:
        """Return all of this pet's tasks."""
        raise NotImplementedError


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
        raise NotImplementedError

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        raise NotImplementedError

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        raise NotImplementedError

    def set_availability(self, minutes: int, start: time, end: time) -> None:
        """Set how much time the owner has today and their day window."""
        raise NotImplementedError


class Scheduler:
    """Builds and explains a daily care plan for an owner's pets."""

    def __init__(self, owner: Owner):
        self.owner = owner
        self.tasks: list[Task] = []
        self.available_minutes: int = owner.available_minutes

    def sort_tasks(self) -> list[Task]:
        """Order tasks by priority (then duration / preferred time)."""
        raise NotImplementedError

    def filter_tasks(self) -> list[Task]:
        """Drop tasks that aren't due today or don't fit in the time available."""
        raise NotImplementedError

    def assign_time_slots(self) -> list[dict]:
        """Give each chosen task a start and end time within the owner's day."""
        raise NotImplementedError

    def detect_conflicts(self) -> list[tuple]:
        """Return pairs of scheduled tasks whose time slots overlap."""
        raise NotImplementedError

    def generate_plan(self) -> list[dict]:
        """Run sort, filter, and slot assignment; return the daily plan."""
        raise NotImplementedError

    def explain_choice(self, task: Task) -> str:
        """Explain in plain language why a task was scheduled or skipped."""
        raise NotImplementedError
