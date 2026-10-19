"""Temporary testing ground: build a sample owner and pets, then exercise sorting,
filtering, and today's schedule in the terminal.

Run with: python main.py
"""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(heading: str, tasks: list[Task]) -> None:
    """Print a heading and one line per task (time, pet, title, priority, status)."""
    print(f"\n{heading}")
    print("-" * 60)
    if not tasks:
        print("(none)")
    for task in tasks:
        when = f"{task.scheduled_time:%H:%M}" if task.scheduled_time else (task.preferred_time or "any")
        status = f"done {task.last_completed}" if task.completed else "pending"
        print(f"{when:<10} {task.pet_name:<6} {task.title:<16} {task.priority:<7} {status}")


def main() -> None:
    owner = Owner("Jordan", available_minutes=120)

    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added deliberately out of order (evening before morning, 18:00 before 08:00)
    # so the sorted output below has something to fix.
    luna.add_task(Task("Laser play", 15, "medium", category="enrichment", scheduled_time=time(18, 0)))
    mochi.add_task(Task("Evening walk", 30, "medium", category="walk", preferred_time="evening"))
    luna.add_task(Task("Full grooming", 90, "low", category="grooming"))
    mochi.add_task(Task("Heartworm meds", 5, "high", category="meds", scheduled_time=time(9, 0)))
    mochi.add_task(Task("Puzzle feeder", 15, "low", category="enrichment", preferred_time="afternoon"))
    luna.add_task(Task("Breakfast", 10, "medium", category="feeding", scheduled_time=time(8, 0)))
    mochi.add_task(Task("Morning walk", 30, "high", category="walk", preferred_time="morning"))
    # Two deliberate clashes to show conflict detection:
    # same pet (both Mochi at 09:00) and different pets (Mochi and Luna at 18:00).
    mochi.add_task(Task("Ear drops", 5, "high", category="meds", scheduled_time=time(9, 0)))
    mochi.add_task(Task("Vet call", 20, "medium", scheduled_time=time(18, 0), frequency="once"))

    scheduler = Scheduler(owner)

    # --- Sorting -----------------------------------------------------------
    print_tasks("All tasks, in the order they were added", owner.get_all_tasks())
    print_tasks("All tasks, sorted by time (Scheduler.sort_by_time)", scheduler.sort_by_time(owner.get_all_tasks()))

    # --- Filtering ---------------------------------------------------------
    print_tasks("Luna's tasks only (filter_tasks(pet_name='Luna'))", owner.filter_tasks(pet_name="Luna"))

    for title in ("Morning walk", "Breakfast"):
        task = next(t for t in owner.get_all_tasks() if t.title == title)
        upcoming = scheduler.mark_task_complete(task)
        print(f"\nMarked {task.title!r} ({task.pet_name}) complete; next one due {upcoming.due_date}")

    print_tasks("Completed tasks (filter_tasks(completed=True))", owner.filter_tasks(completed=True))
    print_tasks(
        "Mochi's pending tasks, sorted by time (filter + sort combined)",
        scheduler.sort_by_time(owner.filter_tasks(pet_name="Mochi", completed=False)),
    )

    # --- Today's schedule --------------------------------------------------
    plan = scheduler.generate_plan()

    print(f"\nToday's Schedule for {owner.name}")
    print("=" * 60)
    for entry in plan:
        task = entry["task"]
        print(
            f"{entry['start']:%H:%M}-{entry['end']:%H:%M}  "
            f"{entry['pet']:<6} {task.title:<16} {'[' + task.priority + ']':<9} {entry['reason']}"
        )

    if scheduler.skipped:
        print("\nSkipped")
        print("-" * 60)
        for task, reason in scheduler.skipped:
            print(f"{task.pet_name:<6} {task.title:<16} {reason}")

    print("\nConflict check")
    print("-" * 60)
    warnings = scheduler.conflict_warnings()
    for warning in warnings:
        print("WARNING: " + warning)
    if not warnings:
        print("No conflicts.")


if __name__ == "__main__":
    main()
