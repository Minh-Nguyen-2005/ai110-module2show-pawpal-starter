"""
main.py — PawPal+ CLI demo script

Run:  python main.py

Demonstrates:
  1. Full scheduling pipeline (unchanged from Phase 2)
  2. Scheduler.sort_by_time()  — tasks added out of order, sorted by HH:MM
  3. Owner.get_all_tasks()     — filter by pet name and completion status
"""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Scheduler

DIVIDER = "─" * 56


# ---------------------------------------------------------------------------
# Build owner + pets
# ---------------------------------------------------------------------------

owner = Owner("Alex", daily_time_budget=90)

biscuit = Pet("Biscuit", species="dog", age=4, notes="Energetic — needs at least one long walk")
biscuit.add_task(Task("Morning walk",    "walk",       duration=30, priority="high"))
biscuit.add_task(Task("Breakfast",       "feeding",    duration=10, priority="high",  fixed_time="07:30"))
biscuit.add_task(Task("Flea treatment",  "medication", duration=5,  priority="high",  fixed_time="09:00"))
biscuit.add_task(Task("Coat brushing",   "grooming",   duration=15, priority="low"))

miso = Pet("Miso", species="cat", age=2, notes="Indoor only — enrichment is important")
miso.add_task(Task("Wet food",           "feeding",    duration=5,  priority="high",  fixed_time="07:30"))
miso.add_task(Task("Puzzle feeder",      "enrichment", duration=15, priority="medium"))
miso.add_task(Task("Litter box clean",   "grooming",   duration=10, priority="medium"))
miso.add_task(Task("Wand toy session",   "enrichment", duration=20, priority="low"))

owner.add_pet(biscuit)
owner.add_pet(miso)


# ---------------------------------------------------------------------------
# Section 1 — Full schedule (existing pipeline)
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner)
scheduler.generate_plan()

print()
print("=" * 56)
print("       🐾  PawPal+  —  Today's Schedule")
print("=" * 56)
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

if scheduler.skipped_tasks:
    print()
    print("  Skipped (not enough time):")
    for task in scheduler.skipped_tasks:
        print(f"    • {task.pet_name}: {task.name}  ({task.duration}min, {task.priority})")

print("=" * 56)


# ---------------------------------------------------------------------------
# Section 2 — sort_by_time() demo
#
# Tasks are added deliberately out of order to prove that sort_by_time()
# uses real datetime.time comparison, not string sort.
# Key trap: string sort puts "9:00" AFTER "10:00" because "9" > "1".
# datetime.time sort correctly places 9:00 BEFORE 10:00.
# ---------------------------------------------------------------------------

print()
print("=" * 56)
print("  DEMO: sort_by_time() — tasks added out of order")
print("=" * 56)

# Intentionally out-of-order fixed times: 10:00, 7:00, 9:00, 8:30
# String sort order would be: "10:00", "7:00", "8:30", "9:00"  ← wrong
# Correct time order should be: 7:00, 8:30, 9:00, 10:00        ← right
mixed_tasks = [
    Task("Evening pills",    "medication", duration=5,  priority="high",   fixed_time="10:00"),
    Task("Early breakfast",  "feeding",    duration=10, priority="high",   fixed_time="7:00"),
    Task("Morning walk",     "walk",       duration=30, priority="medium", fixed_time="9:00"),
    Task("Insulin shot",     "medication", duration=5,  priority="high",   fixed_time="8:30"),
    Task("Playtime",         "enrichment", duration=15, priority="low"),   # no fixed_time
    Task("Grooming",         "grooming",   duration=20, priority="medium"),# no fixed_time
]

print()
print("  Before sorting (insertion order):")
print(f"  {'Task':<20} {'Fixed time'}")
print(DIVIDER)
for t in mixed_tasks:
    print(f"  {t.name:<20} {t.fixed_time or '(flexible)'}")

sorted_tasks = scheduler.sort_by_time(mixed_tasks)

print()
print("  After sort_by_time() — fixed tasks by clock, flexible tasks last:")
print(f"  {'Task':<20} {'Fixed time'}")
print(DIVIDER)
for t in sorted_tasks:
    print(f"  {t.name:<20} {t.fixed_time or '(flexible)'}")

print()
print("  String-sort comparison (to show the bug sort_by_time() avoids):")
string_sorted = sorted(mixed_tasks, key=lambda t: t.fixed_time or "~")  # "~" sorts after all digits
print(f"  {'Task':<20} {'Fixed time'}")
print(DIVIDER)
for t in string_sorted:
    print(f"  {t.name:<20} {t.fixed_time or '(flexible)'}")
print("  ^ Notice '10:00' sorts before '7:00' and '8:30' — incorrect!")

print("=" * 56)


# ---------------------------------------------------------------------------
# Section 3 — get_all_tasks() filtering demo
# ---------------------------------------------------------------------------

print()
print("=" * 56)
print("  DEMO: get_all_tasks() — filtering by pet and status")
print("=" * 56)

# Mark one task complete to make the status filter interesting
biscuit_tasks = owner.get_all_tasks(pet_name="Biscuit")
biscuit_tasks[0].mark_complete()   # mark "Morning walk" done

print()
print("  Filter: pet_name='Biscuit'  (all tasks, any status)")
print(f"  {'Task':<22} {'Status'}")
print(DIVIDER)
for t in owner.get_all_tasks(pet_name="Biscuit"):
    print(f"  {t.name:<22} {'done' if t.is_completed else 'pending'}")

print()
print("  Filter: completed=False  (pending tasks across ALL pets)")
print(f"  {'Pet':<10} {'Task':<22} {'Priority'}")
print(DIVIDER)
for t in owner.get_all_tasks(completed=False):
    print(f"  {t.pet_name:<10} {t.name:<22} {t.priority}")

print()
print("  Filter: pet_name='Biscuit', completed=True  (done tasks for Biscuit only)")
print(f"  {'Task':<22} {'Priority'}")
print(DIVIDER)
done = owner.get_all_tasks(pet_name="Biscuit", completed=True)
if done:
    for t in done:
        print(f"  {t.name:<22} {t.priority}")
else:
    print("  (none)")

print("=" * 56)
print()


# ---------------------------------------------------------------------------
# Section 4 — Recurring tasks demo
#
# pet.complete_task() marks the task done and uses Task.next_occurrence()
# with timedelta to append the next instance automatically.
# ---------------------------------------------------------------------------

print("=" * 56)
print("  DEMO: Recurring tasks + timedelta")
print("=" * 56)

TODAY = date(2026, 4, 6)   # pinned for reproducible output

nova = Pet("Nova", species="rabbit", age=1)

nova.add_task(Task(
    "Morning pellets", "feeding", duration=5, priority="high",
    frequency="daily", due_date=TODAY,
))
nova.add_task(Task(
    "Cage deep-clean", "grooming", duration=30, priority="medium",
    frequency="weekly", due_date=TODAY,
))
nova.add_task(Task(
    "Vet check-up", "medication", duration=60, priority="high",
    frequency="once", due_date=TODAY,
))

def show_tasks(label: str):
    print(f"\n  {label}")
    print(f"  {'Task':<22} {'Freq':<8} {'Due date':<12} {'Status'}")
    print(DIVIDER)
    for t in nova.get_tasks():
        due = str(t.due_date) if t.due_date else "any day"
        status = "done" if t.is_completed else "pending"
        print(f"  {t.name:<22} {t.frequency:<8} {due:<12} {status}")

show_tasks("Before completing any tasks:")

# Complete all three tasks using complete_task() (not mark_complete directly)
next_pellets  = nova.complete_task("Morning pellets",  today=TODAY)
next_clean    = nova.complete_task("Cage deep-clean",  today=TODAY)
next_vet      = nova.complete_task("Vet check-up",     today=TODAY)

show_tasks("After completing all three tasks:")

print()
print("  Next-occurrence dates produced by timedelta:")
if next_pellets:
    print(f"    Morning pellets  (daily)  → {next_pellets.due_date}  "
          f"(+{(next_pellets.due_date - TODAY).days} day)")
if next_clean:
    print(f"    Cage deep-clean  (weekly) → {next_clean.due_date}  "
          f"(+{(next_clean.due_date - TODAY).days} days)")
if next_vet is None:
    print(f"    Vet check-up     (once)   → no next occurrence created  ✓")

# Show what get_pending_tasks returns on TODAY vs TOMORROW
print()
print(f"  get_pending_tasks(today={TODAY})  — tasks due today or earlier:")
pending_today = nova.get_pending_tasks(today=TODAY)
print(f"    {[t.name for t in pending_today]}")

tomorrow = TODAY + timedelta(days=1)
print(f"  get_pending_tasks(today={tomorrow})  — tasks due by tomorrow:")
pending_tomorrow = nova.get_pending_tasks(today=tomorrow)
print(f"    {[t.name for t in pending_tomorrow]}")

print("=" * 56)
print()


# ---------------------------------------------------------------------------
# Section 5 — Conflict detection demo
#
# Three deliberate scenarios to exercise _detect_conflicts():
#   • Exact same time:  Rex breakfast (07:30, 10min) and Luna wet food (07:30, 5min)
#   • Partial overlap:  Rex evening meds (19:50, 20min) ends 20:10,
#                       Luna night walk (20:00, 30min) starts 20:00  → overlap 20:00–20:10
#   • Adjacent (no conflict): Rex morning walk (08:30, 30min) ends exactly 09:00,
#                             Luna physio starts exactly 09:00  → touching, not overlapping
# ---------------------------------------------------------------------------

print("=" * 56)
print("  DEMO: Conflict detection")
print("=" * 56)

conflict_owner = Owner("Sam", daily_time_budget=120)

rex = Pet("Rex", species="dog", age=5)
rex.add_task(Task("Breakfast",    "feeding",    duration=10, priority="high",   fixed_time="07:30"))
rex.add_task(Task("Evening meds", "medication", duration=20, priority="high",   fixed_time="19:50"))
rex.add_task(Task("Morning walk", "walk",       duration=30, priority="medium", fixed_time="08:30"))

luna = Pet("Luna", species="cat", age=3)
luna.add_task(Task("Wet food",    "feeding",    duration=5,  priority="high",   fixed_time="07:30"))
luna.add_task(Task("Night walk",  "walk",       duration=30, priority="medium", fixed_time="20:00"))
luna.add_task(Task("Physio",      "grooming",   duration=15, priority="low",    fixed_time="09:00"))

conflict_owner.add_pet(rex)
conflict_owner.add_pet(luna)

s2 = Scheduler(conflict_owner)
s2.generate_plan()

print()
if s2.conflicts:
    print(f"  ⚠  {len(s2.conflicts)} conflict(s) detected:")
    for warn in s2.conflicts:
        print(f"    {warn}")
else:
    print("  No conflicts detected.")

print()
print("  Schedule still generated (conflicts are warnings, not errors):")
print(f"  {'Pet':<8} {'Task':<18} {'Time':<7} {'Min':>4}  {'Priority'}")
print(DIVIDER)
for t in s2.scheduled_tasks:
    print(f"  {t.pet_name:<8} {t.name:<18} {t.fixed_time or 'flex':<7} {t.duration:>4}  {t.priority}")

print("=" * 56)
print()
