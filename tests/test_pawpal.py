"""Tests for the PawPal+ logic layer (pawpal_system.py)."""

from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

TODAY = date(2026, 10, 18)


def make_owner(minutes: int = 120) -> tuple[Owner, Pet, Pet]:
    owner = Owner("Jordan", available_minutes=minutes)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner, mochi, luna


# --- Task ---------------------------------------------------------------


def test_mark_complete_changes_status():
    task = Task("Walk", 30)
    assert task.completed is False

    task.mark_complete(TODAY)

    assert task.completed is True
    assert task.last_completed == TODAY


def test_daily_task_is_due_again_the_next_day():
    task = Task("Feed", 10, frequency="daily")
    task.mark_complete(TODAY)

    assert task.is_due_today(TODAY) is False
    assert task.is_due_today(TODAY + timedelta(days=1)) is True


def test_weekly_task_is_due_after_seven_days():
    task = Task("Bath", 30, frequency="weekly")
    task.mark_complete(TODAY)

    assert task.is_due_today(TODAY + timedelta(days=6)) is False
    assert task.is_due_today(TODAY + timedelta(days=7)) is True


def test_update_rejects_unknown_fields():
    task = Task("Walk", 30)
    with pytest.raises(ValueError):
        task.update({"colour": "blue"})


# --- Pet ----------------------------------------------------------------


def test_adding_a_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task("Walk", 30))

    assert len(pet.get_tasks()) == 1


def test_add_task_tags_task_with_pet_name():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", 30)

    pet.add_task(task)

    assert task.pet_name == "Mochi"


def test_edit_and_remove_task_by_id():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", 30)
    pet.add_task(task)

    pet.edit_task(task.task_id, {"duration_minutes": 45})
    assert task.duration_minutes == 45

    pet.remove_task(task.task_id)
    assert pet.get_tasks() == []


# --- Owner --------------------------------------------------------------


def test_get_all_tasks_combines_every_pets_tasks():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Walk", 30))
    luna.add_task(Task("Feed", 10))
    luna.add_task(Task("Play", 15))

    titles = {t.title for t in owner.get_all_tasks()}

    assert titles == {"Walk", "Feed", "Play"}


def test_owner_rejects_duplicate_pet_names():
    owner, _, _ = make_owner()
    with pytest.raises(ValueError):
        owner.add_pet(Pet("Mochi", "cat"))


# --- Scheduler ----------------------------------------------------------


def test_plan_includes_tasks_from_multiple_pets():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Walk", 30, "high"))
    luna.add_task(Task("Feed", 10, "high"))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert {entry["pet"] for entry in plan} == {"Mochi", "Luna"}


def test_higher_priority_task_wins_when_time_is_short():
    owner, mochi, _ = make_owner(minutes=30)
    low = Task("Brush", 30, "low")
    high = Task("Walk", 30, "high")
    mochi.add_task(low)
    mochi.add_task(high)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    assert [entry["task"] for entry in plan] == [high]
    assert scheduler.skipped[0][0] is low
    assert "not enough time" in scheduler.explain_choice(low)


def test_completed_task_is_skipped_for_the_day():
    owner, mochi, _ = make_owner()
    task = Task("Feed", 10)
    task.mark_complete(TODAY)
    mochi.add_task(task)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    assert plan == []
    assert "already done" in scheduler.explain_choice(task)


def test_fixed_time_task_is_placed_at_its_time():
    owner, mochi, _ = make_owner()
    mochi.add_task(Task("Meds", 5, "high", scheduled_time=time(9, 0)))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert plan[0]["start"] == time(9, 0)
    assert plan[0]["end"] == time(9, 5)


def test_flexible_task_does_not_overlap_fixed_task():
    owner, mochi, _ = make_owner()
    mochi.add_task(Task("Meds", 10, "high", scheduled_time=time(8, 0)))
    mochi.add_task(Task("Walk", 30, "high"))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    walk = next(e for e in plan if e["task"].title == "Walk")
    assert walk["start"] == time(8, 10)
    assert scheduler.detect_conflicts() == []


def test_detect_conflicts_finds_overlapping_fixed_tasks():
    owner, mochi, luna = make_owner()
    vet = Task("Vet call", 20, scheduled_time=time(9, 0))
    meds = Task("Meds", 20, scheduled_time=time(9, 10))
    mochi.add_task(vet)
    luna.add_task(meds)

    scheduler = Scheduler(owner)
    scheduler.generate_plan(TODAY)

    assert scheduler.detect_conflicts() == [(vet, meds)]


def test_plan_is_sorted_by_start_time():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Play", 15, scheduled_time=time(18, 0)))
    luna.add_task(Task("Breakfast", 10, scheduled_time=time(8, 0)))
    mochi.add_task(Task("Meds", 5, scheduled_time=time(9, 0)))

    plan = Scheduler(owner).generate_plan(TODAY)

    starts = [entry["start"] for entry in plan]
    assert starts == sorted(starts)
