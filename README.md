# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ goes beyond a simple sorted list. Four algorithms make the daily plan more accurate and useful:

**Sort by time**
Fixed-time tasks (e.g. medication at `08:00`) are sorted using `datetime.time` comparison, not raw strings. String sort puts `"9:00"` after `"10:00"` because `"9" > "1"` lexicographically — the datetime-based sort gives the correct clock order every time.

**Filter by pet or status**
`Owner.get_all_tasks(pet_name=..., completed=...)` lets you slice the task list any way you need: all of one pet's tasks, all pending tasks across every pet, or completed tasks for a specific pet. Both parameters are optional and composable.

**Recurring tasks**
Tasks carry a `frequency` field (`"once"` / `"daily"` / `"weekly"`). Calling `Pet.complete_task()` marks the task done and automatically appends the next instance with its due date advanced by `timedelta(days=1)` or `timedelta(weeks=1)`. One-off tasks are never duplicated.

**Conflict detection**
Before building the schedule, `Scheduler._detect_conflicts()` checks every pair of fixed-time tasks for overlapping windows using the interval test `start_a < end_b AND start_b < end_a`. Conflicts are returned as plain-English warning strings — the schedule is still generated so the owner can decide how to resolve them.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
