import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state initialisation — "check before create" pattern
#
# st.session_state works like a dictionary that survives re-runs.
# The guard below means: only create the object on the very first run.
# Every subsequent run finds the key already present and skips the block,
# so the Owner (and everything attached to it) is never reset by a page refresh.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None          # set when the owner form is submitted

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None      # set when Generate Schedule is clicked

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("A smart daily planner for busy pet owners.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.subheader("1. Owner Profile")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        time_budget = st.number_input(
            "Daily time budget (minutes)", min_value=10, max_value=480, value=90, step=10
        )
    submitted = st.form_submit_button("Save owner")

if submitted:
    # Replace (or create) the owner in session state.
    # Preserve existing pets if the owner already existed.
    existing_pets = st.session_state.owner.get_pets() if st.session_state.owner else []
    st.session_state.owner = Owner(owner_name, daily_time_budget=time_budget)
    for pet in existing_pets:
        st.session_state.owner.add_pet(pet)
    st.session_state.scheduler = None   # plan is stale after owner change
    st.success(f"Owner saved: {owner_name} ({time_budget} min/day)")

if st.session_state.owner:
    owner = st.session_state.owner
    st.caption(f"Current owner: **{owner.name}** — {owner.daily_time_budget} min/day")
else:
    st.info("Fill in your profile above to get started.")
    st.stop()   # nothing below makes sense without an owner

# ---------------------------------------------------------------------------
# Section 2 — Add a pet
# ---------------------------------------------------------------------------

st.divider()
st.subheader("2. Add a Pet")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    notes = st.text_input("Notes (optional)", placeholder="e.g. needs twice-daily meds")
    add_pet = st.form_submit_button("Add pet")

if add_pet:
    existing_names = [p.name for p in owner.get_pets()]
    if pet_name in existing_names:
        st.warning(f"A pet named '{pet_name}' already exists.")
    else:
        owner.add_pet(Pet(pet_name, species=species, age=age, notes=notes))
        st.session_state.scheduler = None
        st.success(f"Added {species} '{pet_name}'!")

if owner.get_pets():
    st.caption(f"Pets: {', '.join(p.name for p in owner.get_pets())}")
else:
    st.info("No pets yet — add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Add tasks
# ---------------------------------------------------------------------------

st.divider()
st.subheader("3. Add Tasks")

if not owner.get_pets():
    st.info("Add a pet first before adding tasks.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_pet = st.selectbox("Assign to pet", [p.name for p in owner.get_pets()])
        with col2:
            task_type = st.selectbox(
                "Task type", ["walk", "feeding", "medication", "grooming", "enrichment"]
            )
        task_name = st.text_input("Task name", value="Morning walk")
        col3, col4, col5 = st.columns(3)
        with col3:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col4:
            priority = st.selectbox("Priority", ["high", "medium", "low"])
        with col5:
            fixed_time = st.text_input("Fixed time (HH:MM)", placeholder="optional, e.g. 08:00")
        add_task = st.form_submit_button("Add task")

    if add_task:
        pet_obj = next(p for p in owner.get_pets() if p.name == target_pet)
        pet_obj.add_task(Task(
            name=task_name,
            task_type=task_type,
            duration=int(duration),
            priority=priority,
            fixed_time=fixed_time.strip() or None,
        ))
        st.session_state.scheduler = None
        st.success(f"Task '{task_name}' added to {target_pet}!")

    # Show all tasks currently loaded on every pet
    for pet in owner.get_pets():
        tasks = pet.get_tasks()
        if tasks:
            with st.expander(f"{pet.name}'s tasks ({len(tasks)})", expanded=True):
                st.table([
                    {
                        "Task": t.name,
                        "Type": t.task_type,
                        "Min": t.duration,
                        "Priority": t.priority,
                        "Fixed time": t.fixed_time or "—",
                    }
                    for t in tasks
                ])

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
#
# Q: "If a user submits a form to add a new pet, which class method handles
#    that data, and how does the UI get updated to show the change?"
#
# A: owner.add_pet(Pet(...)) handles it (see Section 2, line ~85).
#    The UI updates automatically because Streamlit re-runs the entire script
#    from top to bottom after every button click or form submit.
#    Since `owner` lives in st.session_state (not a local variable), the
#    updated pet list is still attached to it on the re-run, so every widget
#    that calls owner.get_pets() reflects the new state immediately.
# ---------------------------------------------------------------------------

st.divider()
st.subheader("4. Generate Today's Schedule")

all_tasks = [t for p in owner.get_pets() for t in p.get_pending_tasks()]

if not owner.get_pets():
    st.info("Add at least one pet before generating a schedule.")
elif not all_tasks:
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner)
        scheduler.generate_plan()
        st.session_state.scheduler = scheduler

if st.session_state.scheduler:
    s = st.session_state.scheduler
    time_used = sum(t.duration for t in s.scheduled_tasks)

    # ── Summary header ──────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Tasks scheduled", len(s.scheduled_tasks))
    col_b.metric("Time used (min)", time_used)
    col_c.metric("Time free (min)", s.time_budget - time_used)

    # ── Scheduled tasks table ────────────────────────────────────────────────
    if s.scheduled_tasks:
        st.markdown("#### Scheduled")
        st.table([
            {
                "Pet":       t.pet_name,
                "Task":      t.name,
                "Type":      t.task_type,
                "Min":       t.duration,
                "Priority":  t.priority,
                "Time":      t.fixed_time or "flexible",
            }
            for t in s.scheduled_tasks
        ])

    # ── Skipped tasks ────────────────────────────────────────────────────────
    if s.skipped_tasks:
        st.markdown("#### Skipped (not enough time)")
        st.table([
            {
                "Pet":      t.pet_name,
                "Task":     t.name,
                "Min":      t.duration,
                "Priority": t.priority,
            }
            for t in s.skipped_tasks
        ])

    # ── Reasoning log ────────────────────────────────────────────────────────
    with st.expander("Why did the scheduler choose this plan?"):
        for line in s.explain():
            st.text(line)
