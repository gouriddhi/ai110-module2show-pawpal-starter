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


def test_completed_task_is_no_longer_due():
    task = Task("Feed", 10)
    task.mark_complete(TODAY)

    assert task.is_due_today(TODAY) is False
    assert task.is_due_today(TODAY + timedelta(days=30)) is False


def test_task_with_future_due_date_is_not_due_yet():
    task = Task("Bath", 30, due_date=TODAY + timedelta(days=2))

    assert task.is_due_today(TODAY) is False
    assert task.is_due_today(TODAY + timedelta(days=2)) is True
    assert task.is_due_today(TODAY + timedelta(days=5)) is True  # overdue still counts


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


def test_completing_daily_task_creates_one_due_tomorrow():
    pet = Pet("Mochi", "dog")
    walk = Task("Walk", 30, "high", frequency="daily", preferred_time="morning")
    pet.add_task(walk)

    upcoming = pet.complete_task(walk.task_id, TODAY)

    assert walk.completed is True
    assert upcoming in pet.get_tasks()
    assert upcoming.due_date == TODAY + timedelta(days=1)
    assert upcoming.completed is False
    assert upcoming.task_id != walk.task_id
    assert (upcoming.title, upcoming.preferred_time, upcoming.pet_name) == ("Walk", "morning", "Mochi")


def test_completing_weekly_task_creates_one_due_in_seven_days():
    pet = Pet("Luna", "cat")
    bath = Task("Bath", 30, frequency="weekly")
    pet.add_task(bath)

    upcoming = pet.complete_task(bath.task_id, TODAY)

    assert upcoming.due_date == TODAY + timedelta(days=7)


def test_completing_one_off_task_does_not_repeat():
    pet = Pet("Mochi", "dog")
    vet = Task("Vet visit", 60, frequency="once")
    pet.add_task(vet)

    assert pet.complete_task(vet.task_id, TODAY) is None
    assert pet.get_tasks() == [vet]


def test_completing_a_task_twice_is_rejected():
    pet = Pet("Mochi", "dog")
    walk = Task("Walk", 30)
    pet.add_task(walk)
    pet.complete_task(walk.task_id, TODAY)

    with pytest.raises(ValueError):
        pet.complete_task(walk.task_id, TODAY)


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


def test_filter_tasks_by_pet_and_status():
    owner, mochi, luna = make_owner()
    walk, meds = Task("Walk", 30), Task("Meds", 5)
    feed = Task("Feed", 10)
    mochi.add_task(walk)
    mochi.add_task(meds)
    luna.add_task(feed)
    meds.mark_complete(TODAY)

    assert owner.filter_tasks(pet_name="Mochi") == [walk, meds]
    assert owner.filter_tasks(completed=False) == [walk, feed]
    assert owner.filter_tasks(pet_name="Mochi", completed=True) == [meds]
    assert owner.filter_tasks() == owner.get_all_tasks()
    assert owner.filter_tasks(pet_name="Rex") == []


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


def test_unplaceable_fixed_task_does_not_use_up_the_time_budget():
    owner, mochi, _ = make_owner(minutes=30)  # owner's day is 08:00-20:00
    late_meds = Task("Late meds", 30, "high", scheduled_time=time(21, 0))
    walk = Task("Walk", 30, "low")
    mochi.add_task(late_meds)
    mochi.add_task(walk)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    assert [entry["task"] for entry in plan] == [walk]
    assert "outside the owner's day" in scheduler.explain_choice(late_meds)


def test_flexible_task_with_no_free_slot_gives_its_time_back():
    owner, mochi, _ = make_owner(minutes=300)
    # Evening starts at 17:00 and the day ends at 20:00, so 200 minutes can't fit.
    long_play = Task("Long play", 200, "high", preferred_time="evening")
    grooming = Task("Grooming", 120, "low")
    mochi.add_task(long_play)
    mochi.add_task(grooming)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    assert [entry["task"] for entry in plan] == [grooming]
    assert "no free slot" in scheduler.explain_choice(long_play)


def test_plan_is_sorted_by_start_time():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Play", 15, scheduled_time=time(18, 0)))
    luna.add_task(Task("Breakfast", 10, scheduled_time=time(8, 0)))
    mochi.add_task(Task("Meds", 5, scheduled_time=time(9, 0)))

    plan = Scheduler(owner).generate_plan(TODAY)

    starts = [entry["start"] for entry in plan]
    assert starts == sorted(starts)


def test_sort_by_time_puts_fixed_times_first_then_preferred_time():
    owner, mochi, _ = make_owner()
    evening = Task("Play", 15, preferred_time="evening")
    anytime = Task("Brush", 10)
    late = Task("Dinner", 10, scheduled_time=time(18, 0))
    morning = Task("Walk", 30, preferred_time="morning")
    early = Task("Meds", 5, scheduled_time=time(7, 30))

    ordered = Scheduler(owner).sort_by_time([evening, anytime, late, morning, early])

    assert ordered == [early, late, morning, evening, anytime]


def test_sort_by_time_returns_tasks_in_chronological_order():
    owner, _, _ = make_owner()
    dinner = Task("Dinner", 10, scheduled_time=time(18, 0))
    late_meds = Task("Meds", 5, scheduled_time=time(9, 30))
    breakfast = Task("Breakfast", 10, scheduled_time=time(7, 5))
    early_meds = Task("Eye drops", 5, scheduled_time=time(9, 5))
    lunch = Task("Lunch", 10, scheduled_time=time(12, 30))
    added = [dinner, late_meds, breakfast, early_meds, lunch]  # deliberately out of order

    ordered = Scheduler(owner).sort_by_time(added)

    assert [t.scheduled_time for t in ordered] == [time(7, 5), time(9, 5), time(9, 30), time(12, 30), time(18, 0)]
    assert added == [dinner, late_meds, breakfast, early_meds, lunch]  # input list is left unchanged


def test_next_occurrence_is_not_scheduled_until_it_is_due():
    owner, mochi, _ = make_owner()
    walk = Task("Walk", 30, "high")
    mochi.add_task(walk)
    upcoming = mochi.complete_task(walk.task_id, TODAY)

    scheduler = Scheduler(owner)
    assert scheduler.generate_plan(TODAY) == []
    assert "not due until" in scheduler.explain_choice(upcoming)

    plan = scheduler.generate_plan(TODAY + timedelta(days=1))
    assert [entry["task"] for entry in plan] == [upcoming]


def test_back_to_back_tasks_are_not_a_conflict():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Meds", 30, scheduled_time=time(9, 0)))
    luna.add_task(Task("Feed", 10, scheduled_time=time(9, 30)))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(TODAY)

    assert scheduler.detect_conflicts() == []
    assert scheduler.conflict_warnings() == []


def test_conflict_warning_describes_the_overlap():
    owner, mochi, luna = make_owner()
    mochi.add_task(Task("Vet call", 20, scheduled_time=time(9, 0)))
    luna.add_task(Task("Meds", 20, scheduled_time=time(9, 10)))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(TODAY)

    assert scheduler.conflict_warnings() == [
        "Different pets: Vet call (Mochi) 09:00-09:20 overlaps Meds (Luna) 09:10-09:30 by 10 min"
    ]


def test_conflict_warning_flags_same_pet_at_the_same_time():
    owner, mochi, _ = make_owner()
    mochi.add_task(Task("Heartworm meds", 5, "high", scheduled_time=time(9, 0)))
    mochi.add_task(Task("Ear drops", 5, "high", scheduled_time=time(9, 0)))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)  # conflicts don't stop the plan from being built

    assert len(plan) == 2
    assert scheduler.conflict_warnings() == [
        "Same pet (Mochi): Heartworm meds 09:00-09:05 overlaps Ear drops 09:00-09:05 by 5 min"
    ]


def test_conflict_warnings_is_empty_before_a_plan_exists():
    owner, mochi, _ = make_owner()
    mochi.add_task(Task("Meds", 5, scheduled_time=time(9, 0)))
    mochi.add_task(Task("Drops", 5, scheduled_time=time(9, 0)))

    assert Scheduler(owner).conflict_warnings() == []


def test_detect_conflicts_finds_every_overlapping_pair():
    owner, mochi, luna = make_owner(minutes=300)
    long_task = Task("Grooming", 60, scheduled_time=time(9, 0))
    a = Task("Meds", 10, scheduled_time=time(9, 10))
    b = Task("Feed", 10, scheduled_time=time(9, 40))
    mochi.add_task(long_task)
    mochi.add_task(a)
    luna.add_task(b)

    scheduler = Scheduler(owner)
    scheduler.generate_plan(TODAY)

    assert scheduler.detect_conflicts() == [(long_task, a), (long_task, b)]


@pytest.mark.parametrize("same_pet", [True, False])
def test_detect_conflicts_flags_tasks_at_the_exact_same_time(same_pet):
    owner, mochi, luna = make_owner()
    walk = Task("Walk", 30, scheduled_time=time(9, 0))
    meds = Task("Meds", 5, scheduled_time=time(9, 0))
    mochi.add_task(walk)
    (mochi if same_pet else luna).add_task(meds)

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(TODAY)

    conflicts = scheduler.detect_conflicts()
    assert len(plan) == 2  # both stay in the plan; the scheduler warns instead of dropping one
    assert len(conflicts) == 1
    assert {t.title for t in conflicts[0]} == {"Walk", "Meds"}  # same start time, so pair order doesn't matter
    assert len(scheduler.conflict_warnings()) == 1
    assert scheduler.conflict_warnings()[0].startswith("Same pet" if same_pet else "Different pets")


def test_three_tasks_at_the_same_time_report_every_pair():
    owner, mochi, luna = make_owner()
    a = Task("Meds", 5, scheduled_time=time(9, 0))
    b = Task("Feed", 5, scheduled_time=time(9, 0))
    c = Task("Brush", 5, scheduled_time=time(9, 0))
    mochi.add_task(a)
    mochi.add_task(b)
    luna.add_task(c)

    scheduler = Scheduler(owner)
    scheduler.generate_plan(TODAY)

    assert len(scheduler.detect_conflicts()) == 3  # a-b, a-c, b-c


def test_scheduler_mark_task_complete_creates_next_daily_and_weekly_instances():
    owner, mochi, luna = make_owner()
    walk = Task("Walk", 30, "high", frequency="daily")
    bath = Task("Bath", 20, frequency="weekly")
    mochi.add_task(walk)
    luna.add_task(bath)
    scheduler = Scheduler(owner)

    next_walk = scheduler.mark_task_complete(walk, TODAY)
    next_bath = scheduler.mark_task_complete(bath, TODAY)

    assert walk.completed and bath.completed
    assert next_walk in mochi.get_tasks() and next_walk.pet_name == "Mochi"
    assert next_bath in luna.get_tasks() and next_bath.pet_name == "Luna"
    assert next_walk.due_date == TODAY + timedelta(days=1)
    assert next_bath.due_date == TODAY + timedelta(days=7)
    assert owner.filter_tasks(completed=False) == [next_walk, next_bath]


def test_scheduler_mark_task_complete_rejects_task_without_a_known_pet():
    owner, _, _ = make_owner()
    stray = Task("Walk", 30)  # never added to a pet, so pet_name is ""

    with pytest.raises(KeyError):
        Scheduler(owner).mark_task_complete(stray, TODAY)


@pytest.mark.parametrize(
    "done_on, expected",
    [
        (date(2026, 10, 18), date(2026, 10, 19)),  # ordinary day
        (date(2026, 10, 31), date(2026, 11, 1)),  # end of month
        (date(2026, 12, 31), date(2027, 1, 1)),  # end of year
        (date(2028, 2, 28), date(2028, 2, 29)),  # leap year
        (date(2027, 2, 28), date(2027, 3, 1)),  # non-leap year
    ],
)
def test_daily_next_due_date_is_completion_day_plus_one(done_on, expected):
    owner, mochi, _ = make_owner()
    walk = Task("Walk", 30, frequency="daily")
    mochi.add_task(walk)

    upcoming = Scheduler(owner).mark_task_complete(walk, done_on)

    assert upcoming.due_date == expected


def test_daily_next_due_date_defaults_to_today_plus_one():
    owner, mochi, _ = make_owner()
    walk = Task("Walk", 30, frequency="daily")
    mochi.add_task(walk)

    upcoming = Scheduler(owner).mark_task_complete(walk)

    assert walk.last_completed == date.today()
    assert upcoming.due_date == date.today() + timedelta(days=1)


def test_frequency_is_case_and_space_insensitive():
    owner, mochi, _ = make_owner()
    walk = Task("Walk", 30, frequency="Daily")
    bath = Task("Bath", 20, frequency=" WEEKLY ")
    mochi.add_task(walk)
    mochi.add_task(bath)
    scheduler = Scheduler(owner)

    assert walk.frequency == "daily"
    assert scheduler.mark_task_complete(walk, TODAY).due_date == TODAY + timedelta(days=1)
    assert scheduler.mark_task_complete(bath, TODAY).due_date == TODAY + timedelta(days=7)


def test_unknown_frequency_is_rejected():
    with pytest.raises(ValueError):
        Task("Walk", 30, frequency="monthly")

    task = Task("Walk", 30)
    with pytest.raises(ValueError):
        task.update({"frequency": "every other day"})
    assert task.frequency == "daily"  # a rejected edit leaves the task unchanged

    task.update({"frequency": "Weekly"})
    assert task.frequency == "weekly"
