"""Temporary testing ground: build a sample owner and pets, then print today's schedule.

Run with: python main.py
"""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner("Jordan", available_minutes=120)

    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.add_task(Task("Morning walk", 30, "high", category="walk", preferred_time="morning"))
    mochi.add_task(Task("Heartworm meds", 5, "high", category="meds", scheduled_time=time(9, 0)))
    luna.add_task(Task("Breakfast", 10, "medium", category="feeding", scheduled_time=time(8, 0)))
    luna.add_task(Task("Laser play", 15, "medium", category="enrichment", scheduled_time=time(18, 0)))
    luna.add_task(Task("Full grooming", 90, "low", category="grooming"))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    print(f"Today's Schedule for {owner.name}")
    print("=" * 50)
    for entry in plan:
        task = entry["task"]
        print(
            f"{entry['start']:%H:%M}-{entry['end']:%H:%M}  "
            f"{entry['pet']:<6} {task.title:<16} {'[' + task.priority + ']':<9} {entry['reason']}"
        )

    if scheduler.skipped:
        print("\nSkipped")
        print("-" * 50)
        for task, reason in scheduler.skipped:
            print(f"{task.pet_name:<6} {task.title:<16} {reason}")

    conflicts = scheduler.detect_conflicts()
    if conflicts:
        print("\nConflicts")
        print("-" * 50)
        for a, b in conflicts:
            print(f"{a.title} ({a.pet_name}) overlaps {b.title} ({b.pet_name})")


if __name__ == "__main__":
    main()
