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
    st.success(st.session_state.pop("flash"))

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
                    "Pet": t.pet_name,
                    "Task": t.title,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority,
                    "When": f"{t.scheduled_time:%H:%M}" if t.scheduled_time else (t.preferred_time or "any"),
                    "Repeats": t.frequency,
                    "Due": f"{t.due_date:%b %d}" if t.due_date and t.due_date > date.today() else "today",
                    "Status": f"done {t.last_completed:%b %d}" if t.completed else "pending",
                }
                for t in Scheduler(owner).sort_by_time(shown)
            ]
        )
    else:
        st.caption("No tasks match these filters.")

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
if st.button("Generate schedule", disabled=not tasks):
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    if plan:
        st.markdown(f"#### Today's schedule for {owner.name}")
        st.table(
            [
                {
                    "Time": f"{e['start']:%H:%M}–{e['end']:%H:%M}",
                    "Pet": e["pet"],
                    "Task": e["task"].title,
                    "Priority": e["task"].priority,
                    "Why": e["reason"],
                }
                for e in plan
            ]
        )
        scheduled = sum(e["task"].duration_minutes for e in plan)
        st.caption(f"{len(plan)} tasks, {scheduled} of {owner.available_minutes} minutes used.")
    else:
        st.warning("Nothing could be scheduled today.")

    for warning in scheduler.conflict_warnings():
        st.warning(f"⚠️ Conflict: {warning}. Move one of these tasks or change its time.")

    if scheduler.skipped:
        st.markdown("#### Skipped")
        for task, _ in scheduler.skipped:
            st.write("- " + scheduler.explain_choice(task))
