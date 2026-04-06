"""
main.py — PawPal+ CLI demo script

Run:  python main.py

Verifies the full pipeline:
  Owner → Pets → Tasks → Scheduler → printed daily plan
"""

from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Build the owner
# ---------------------------------------------------------------------------

owner = Owner("Alex", daily_time_budget=90)  # 90 minutes available today


# ---------------------------------------------------------------------------
# Build pets and their tasks
# ---------------------------------------------------------------------------

# --- Dog: Biscuit ---
biscuit = Pet("Biscuit", species="dog", age=4, notes="Energetic — needs at least one long walk")

biscuit.add_task(Task(
    name="Morning walk",
    task_type="walk",
    duration=30,
    priority="high",
))
biscuit.add_task(Task(
    name="Breakfast",
    task_type="feeding",
    duration=10,
    priority="high",
    fixed_time="07:30",
))
biscuit.add_task(Task(
    name="Flea treatment",
    task_type="medication",
    duration=5,
    priority="high",
    fixed_time="09:00",
    notes="Apply between shoulder blades",
))
biscuit.add_task(Task(
    name="Coat brushing",
    task_type="grooming",
    duration=15,
    priority="low",
))

# --- Cat: Miso ---
miso = Pet("Miso", species="cat", age=2, notes="Indoor only — enrichment is important")

miso.add_task(Task(
    name="Wet food",
    task_type="feeding",
    duration=5,
    priority="high",
    fixed_time="07:30",
))
miso.add_task(Task(
    name="Puzzle feeder",
    task_type="enrichment",
    duration=15,
    priority="medium",
))
miso.add_task(Task(
    name="Litter box clean",
    task_type="grooming",
    duration=10,
    priority="medium",
))
miso.add_task(Task(
    name="Wand toy session",
    task_type="enrichment",
    duration=20,
    priority="low",
))

# ---------------------------------------------------------------------------
# Register pets with owner
# ---------------------------------------------------------------------------

owner.add_pet(biscuit)
owner.add_pet(miso)


# ---------------------------------------------------------------------------
# Run the scheduler
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner)
scheduler.generate_plan()


# ---------------------------------------------------------------------------
# Print Today's Schedule
# ---------------------------------------------------------------------------

DIVIDER = "─" * 52

print()
print("=" * 52)
print("       🐾  PawPal+  —  Today's Schedule")
print("=" * 52)
print(f"  Owner : {owner.name}")
print(f"  Budget: {owner.daily_time_budget} minutes")
print(f"  Pets  : {', '.join(p.name for p in owner.get_pets())}")
print(DIVIDER)

if scheduler.scheduled_tasks:
    time_used = sum(t.duration for t in scheduler.scheduled_tasks)
    print(f"  {'#':<3} {'Pet':<8} {'Task':<22} {'Type':<12} {'Min':>4}  {'Priority'}")
    print(DIVIDER)
    for i, task in enumerate(scheduler.scheduled_tasks, start=1):
        time_tag = f" @ {task.fixed_time}" if task.fixed_time else ""
        print(
            f"  {i:<3} {task.pet_name:<8} {task.name:<22} "
            f"{task.task_type:<12} {task.duration:>4}  "
            f"{task.priority}{time_tag}"
        )
    print(DIVIDER)
    print(f"  Time used : {time_used} / {owner.daily_time_budget} min")
    print(f"  Time free : {owner.daily_time_budget - time_used} min")
else:
    print("  No tasks scheduled today.")

if scheduler.skipped_tasks:
    print()
    print("  Skipped (not enough time):")
    for task in scheduler.skipped_tasks:
        print(f"    • {task.pet_name}: {task.name}  ({task.duration}min, {task.priority})")

print(DIVIDER)
print()
print("  Reasoning:")
for line in scheduler.explain():
    print(f"    {line}")

print("=" * 52)
print()
