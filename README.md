# PawPal+ — Smart Pet Care Planner

PawPal+ is a Streamlit app that helps busy pet owners stay consistent with daily care. Enter your pets, define their tasks, and let the scheduler build an optimised plan that fits your available time — with plain-English reasoning for every decision.

---

## 📸 Demo

<a href="ai110-module2show-pawpal-starter/pawpal_screenshot.png" target="_blank">
  <img src='ai110-module2show-pawpal-starter/pawpal_screenshot.png' title='PawPal+ App' width='' alt='PawPal App' class='center-block' />
</a>

---

## Features

### Owner and pet management
- Register an owner with a daily time budget (in minutes)
- Add any number of pets with name, species, age, and care notes
- All data persists across page interactions using `st.session_state`

### Task management
- Add tasks to individual pets: **walk**, **feeding**, **medication**, **grooming**, or **enrichment**
- Set duration, priority (`high` / `medium` / `low`), and an optional fixed start time (`HH:MM`)
- Mark tasks as `once`, `daily`, or `weekly` — recurring tasks auto-schedule the next instance on completion

### Sorting by time
Tasks with a fixed start time are sorted using `datetime.time` comparison, not raw strings. Raw string sort incorrectly places `"9:00"` after `"10:00"` (because `'9' > '1'` character-by-character). The datetime-based sort gives correct clock order every time.

### Priority-based scheduling
Flexible tasks (no fixed time) are ordered by priority score (`high=3`, `medium=2`, `low=1`). Within the same priority tier, shorter tasks are scheduled first — a greedy strategy that maximises the number of tasks that fit inside a tight time budget.

### Conflict detection
Before building the schedule, the planner checks every pair of fixed-time tasks for overlapping windows using the interval test:

```
start_a < end_b  AND  start_b < end_a
```

Detected conflicts are shown as amber warnings directly above the schedule. The plan is still generated so the owner can decide how to resolve the clash — adjacent tasks (`end_a == start_b`) are correctly not flagged.

### Recurring tasks
Completing a `daily` task automatically creates the next instance due tomorrow (`due_date + timedelta(days=1)`). A `weekly` task schedules the next instance in 7 days. `once` tasks are never duplicated. Future-dated instances are hidden from today's plan until their due date arrives.

### Filter by pet or status
`Owner.get_all_tasks(pet_name=..., completed=...)` slices the task list across all pets. Both filters are optional and composable — e.g. all pending tasks for one pet, or all completed tasks across every pet.

### Transparent reasoning
Every scheduling decision is logged in plain English:
```
SCHEDULED  Mochi: Breakfast (10min, high, fixed @ 07:30) — 80min remaining.
SKIPPED    Mochi: Nail trim (20min needed, only 10min left).
```
The full log is available in the "Why did the scheduler choose this plan?" expander in the UI.

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the CLI demo

```bash
python main.py
```

---

## Testing PawPal+

### Run the tests

```bash
python -m pytest
```

To see each test name as it runs:

```bash
python -m pytest -v
```

### What the tests cover

The suite lives in `tests/test_pawpal.py` and contains **34 tests** across six classes:

| Class | Tests | Behaviour verified |
|---|---|---|
| `TestTask` | 3 | `mark_complete()` flips status; `priority_score()` returns correct integers |
| `TestPet` | 4 | Tasks added, removed, and filtered correctly by completion status |
| `TestScheduler` | 5 | Priority ordering, fixed-time ordering, budget enforcement, empty-owner edge case |
| `TestSortByTime` | 4 | Clock-order sort including the `"9:00"` vs `"10:00"` string-sort regression guard |
| `TestRecurringTasks` | 8 | Daily/weekly recurrence creates correct next due dates; `once` tasks never duplicated; future-dated tasks hidden from today's plan |
| `TestConflictDetection` | 6 | Exact-time and partial-overlap conflicts flagged; adjacent tasks not flagged; plan still generated when conflicts exist |
| `TestFiltering` | 4 | `get_all_tasks()` filters by pet name, completion status, both combined, and no filter |

### Confidence level

★★★★☆ (4 / 5)

Core scheduling contracts, all four Phase 4 algorithms, and the most important edge cases are covered. The one star short of five reflects two open gaps:

- No integration test for the full Owner → Pet → Task → Scheduler → UI pipeline end-to-end.
- `fixed_time` format validation exists in the UI but has no dedicated unit test; a malformed value would crash `sort_by_time()`.

---

## Project structure

```
pawpal_system.py   — backend logic (Owner, Pet, Task, Scheduler)
app.py             — Streamlit UI
main.py            — CLI demo script
tests/
  test_pawpal.py   — 34-test automated suite
uml_final.png      — final class diagram
uml_final.mmd      — Mermaid source for the diagram
reflection.md      — design decisions and project reflection
```

---

## Smarter scheduling — algorithm notes

**Greedy vs optimal scheduling**
The scheduler uses a greedy first-fit algorithm (O(n)), not an optimal knapsack solver (O(n × W)). This is a deliberate tradeoff: greedy output is transparent and easy to explain to the user. An optimal algorithm might deprioritise a high-priority medication task because three grooming tasks together score higher in aggregate — the wrong outcome for this domain.

**Conflict detection complexity**
`_detect_conflicts()` checks every unique pair of fixed-time tasks using `itertools.combinations` — O(n²) where n is the number of fixed-time tasks. For a typical day with fewer than 10 fixed tasks, this is at most 45 comparisons and runs in under 1ms. An O(n log n) sweep-line algorithm would be faster at scale but would add complexity without any practical benefit here.
