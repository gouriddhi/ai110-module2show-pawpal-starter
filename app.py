from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan your pets' daily care around the time you actually have.")

# Streamlit reruns this whole script on every interaction, so the Owner (and
# everything attached to it) lives in session_state and is only created once.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
owner: Owner = st.session_state.owner

# --- Owner ---------------------------------------------------------------

st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
col1, col2, col3 = st.columns(3)
with col1:
    minutes = st.number_input(
        "Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes
    )
with col2:
    day_start = st.time_input("Day starts", value=owner.day_start)
with col3:
    day_end = st.time_input("Day ends", value=owner.day_end)
try:
    owner.set_availability(int(minutes), day_start, day_end)
except ValueError as err:
    st.error(err)

st.divider()

# --- Add a pet -----------------------------------------------------------

st.subheader("Add a pet")
with st.form("add_pet", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Give your pet a name.")
        else:
            try:
                owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age)))
                st.success(f"Added {pet_name.strip()}.")
            except ValueError as err:
                st.error(err)

if owner.pets:
    st.write("Your pets: " + ", ".join(f"**{p.name}** ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a task ----------------------------------------------------------

st.subheader("Add a task")
if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task", clear_on_submit=True):
        pet_choice = st.selectbox("For which pet?", [p.name for p in owner.pets])
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", placeholder="Morning walk")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        col1, col2, col3 = st.columns(3)
        with col1:
            fixed_time = st.time_input("Fixed time (optional)", value=None, step=300)
        with col2:
            preferred = st.selectbox("Preferred time", ["any", "morning", "afternoon", "evening"])
        with col3:
            frequency = st.selectbox("Repeats", ["daily", "weekly", "once"])
        if st.form_submit_button("Add task"):
            if not task_title.strip():
                st.error("Give the task a title.")
            else:
                pet = next(p for p in owner.pets if p.name == pet_choice)
                pet.add_task(
                    Task(
                        title=task_title.strip(),
                        duration_minutes=int(duration),
                        priority=priority,
                        scheduled_time=fixed_time,
                        preferred_time=None if preferred == "any" else preferred,
                        frequency=frequency,
                    )
                )
                st.success(f"Added '{task_title.strip()}' for {pet.name}.")

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"), icon="✅")

PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}


def due_label(task: Task, today: date) -> str:
    """Short 'Due' column text, based on Task.is_due_today()."""
    if task.completed:
        return "—"
    if task.is_due_today(today):
        return f"overdue since {task.due_date:%b %d}" if task.due_date and task.due_date < today else "today"
    return f"{task.due_date:%b %d}"


def span(entry: dict) -> str:
    """A plan entry's time range, e.g. '09:00–09:05'."""
    return f"{entry['start']:%H:%M}–{entry['end']:%H:%M}"


tasks = owner.get_all_tasks()
if tasks:
    st.markdown("#### Tasks")
    col1, col2 = st.columns(2)
    with col1:
        pet_filter = st.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
    with col2:
        status_filter = st.selectbox("Status", ["Pending", "Completed", "All"])
    shown = owner.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"Pending": False, "Completed": True, "All": None}[status_filter],
    )
    if shown:
        st.table(
            [
                {
                    "When": f"{t.scheduled_time:%H:%M}" if t.scheduled_time else (t.preferred_time or "any time").capitalize(),
                    "Pet": t.pet_name,
                    "Task": t.title,
                    "Priority": PRIORITY_BADGE.get(t.priority, t.priority),
                    "Minutes": t.duration_minutes,
                    "Repeats": t.frequency.capitalize(),
                    "Due": due_label(t, date.today()),
                    "Status": f"✅ Done {t.last_completed:%b %d}" if t.completed else "⏳ Pending",
                }
                for t in Scheduler(owner).sort_by_time(shown)
            ],
            hide_index=True,
        )
        st.caption(f"Showing {len(shown)} of {len(tasks)} tasks, sorted by time of day.")
    else:
        st.info("No tasks match these filters.", icon="🔍")

    pending = {t.task_id: t for t in owner.filter_tasks(completed=False)}
    if pending:
        with st.form("complete_task"):
            done_id = st.selectbox(
                "Mark a task done",
                list(pending),
                format_func=lambda tid: f"{pending[tid].title} ({pending[tid].pet_name})",
            )
            if st.form_submit_button("Mark complete"):
                task = pending[done_id]
                upcoming = Scheduler(owner).mark_task_complete(task)
                message = f"Marked '{task.title}' done for {task.pet_name}."
                if upcoming:
                    message += f" Next one is due {upcoming.due_date:%b %d}."
                # Rerun so the table above shows the change; the message survives via session_state.
                st.session_state.flash = message
                st.rerun()

st.divider()

# --- Schedule ------------------------------------------------------------

st.subheader("Build schedule")
if st.button("Generate schedule", type="primary", disabled=not tasks):
    st.session_state.show_schedule = True

# st.button is only True on the rerun right after the click, so remember that a schedule
# was requested and rebuild it on every rerun. It then stays visible while you filter or
# complete tasks, and always reflects the latest changes.
if st.session_state.get("show_schedule") and tasks:
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()
    conflicts = scheduler.detect_conflicts()
    slots = {id(e["task"]): e for e in plan}
    in_conflict = {id(task) for pair in conflicts for task in pair}
    used = sum(e["task"].duration_minutes for e in plan)

    st.markdown(f"#### Today's schedule for {owner.name}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Scheduled", len(plan), border=True)
    col2.metric("Minutes used", f"{used} / {owner.available_minutes}", border=True)
    col3.metric("Conflicts", len(conflicts), border=True)
    col4.metric("Not scheduled", len(scheduler.skipped), border=True)

    # One warning per conflict: what clashes in plain words, then a concrete fix.
    for first, second in conflicts:
        a, b = slots[id(first)], slots[id(second)]
        if first.pet_name == second.pet_name:
            problem = (
                f"**{first.pet_name} has two tasks at once:** {first.title} ({span(a)}) "
                f"and {second.title} ({span(b)})."
            )
        else:
            problem = (
                f"**You can't be in two places at once:** {first.title} for {first.pet_name} ({span(a)}) "
                f"and {second.title} for {second.pet_name} ({span(b)})."
            )
        move, new_time = scheduler.suggest_fix(first, second)
        if new_time:
            tip = f"💡 Suggestion: move **{move.title}** ({move.priority} priority) to **{new_time:%H:%M}**, the next free time."
        else:
            tip = f"💡 No free gap today is long enough for **{move.title}**. Try shortening it or doing it another day."
        st.warning(f"{problem}\n\n{tip}", icon="⚠️")
    if plan and not conflicts:
        st.success("No time conflicts. This plan works as written.", icon="✅")

    if plan:
        st.table(
            [
                {
                    "Time": span(e),
                    "Pet": e["pet"],
                    "Task": ("⚠️ " if id(e["task"]) in in_conflict else "") + e["task"].title,
                    "Priority": PRIORITY_BADGE.get(e["task"].priority, e["task"].priority),
                    "Why this slot": e["reason"].capitalize(),
                }
                for e in plan
            ],
            hide_index=True,
        )
        st.caption("Updates automatically as you add or complete tasks.")
    else:
        st.info("Nothing could be scheduled today. See below for why.", icon="ℹ️")

    if scheduler.skipped:
        st.markdown("#### Not scheduled today")
        st.table(
            [
                {"Pet": task.pet_name, "Task": task.title, "Reason": reason[0].upper() + reason[1:]}
                for task, reason in scheduler.skipped
            ],
            hide_index=True,
        )
