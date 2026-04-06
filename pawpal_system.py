"""
pawpal_system.py — PawPal+ backend logic layer

Classes (in dependency order):
    Task      — a single care action (dataclass)
    Pet       — a pet and its assigned tasks (dataclass)
    Owner     — an owner, their time budget, and their pets
    Scheduler — scheduling algorithm that produces a daily plan
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care action."""

    name: str
    task_type: str          # walk | feeding | medication | grooming | enrichment
    duration: int           # estimated minutes
    priority: str           # "high" | "medium" | "low"
    fixed_time: str | None = None   # optional hard start, e.g. "08:00"
    is_completed: bool = False
    notes: str = ""
    pet_name: str = ""      # set by Scheduler._collect_all_tasks; used in summaries

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.is_completed = True

    def priority_score(self) -> int:
        """Return a sortable integer: high=3, medium=2, low=1."""
        return {"high": 3, "medium": 2, "low": 1}.get(self.priority, 0)

    def __str__(self) -> str:
        """Return a readable one-line summary of the task for terminal output."""
        status = "done" if self.is_completed else "pending"
        time_part = f" @ {self.fixed_time}" if self.fixed_time else ""
        return (
            f"{self.name} [{self.task_type}, {self.duration}min, "
            f"{self.priority} priority{time_part}] ({status})"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet and the care tasks assigned to it."""

    name: str
    species: str            # e.g. "dog", "cat", "rabbit"
    age: int                # years
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove a task by name (no-op if not found)."""
        self.tasks = [t for t in self.tasks if t.name != task_name]

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        return self.tasks

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been completed today."""
        return [t for t in self.tasks if not t.is_completed]


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """An owner profile with a daily time budget and a list of pets."""

    def __init__(self, name: str, daily_time_budget: int) -> None:
        """Initialise the owner with a name and a daily care time budget in minutes."""
        self.name = name
        self.daily_time_budget = daily_time_budget  # minutes available per day
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's household."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name (no-op if not found)."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return self.pets

    def __repr__(self) -> str:
        """Return an unambiguous string representation useful for debugging."""
        return (
            f"Owner(name={self.name!r}, "
            f"daily_time_budget={self.daily_time_budget}min, "
            f"pets={[p.name for p in self.pets]})"
        )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Produces a daily care plan for an owner's pets.

    Algorithm outline (to be implemented):
        1. Collect all pending tasks from every pet.
        2. Pin fixed-time tasks first (e.g. medication at 08:00).
        3. Sort remaining tasks: priority high→low, then shortest duration first.
        4. Greedily add tasks until the owner's time budget is exhausted.
        5. Record a reasoning note for each decision.
    """

    def __init__(self, owner: Owner) -> None:
        """Bind the scheduler to an owner and initialise empty plan state."""
        self.owner = owner
        self.time_budget: int = owner.daily_time_budget
        self.scheduled_tasks: list[Task] = []
        self.skipped_tasks: list[Task] = []
        self.reasoning_log: list[str] = []

    def generate_plan(self) -> list[Task]:
        """Reset state, run the full scheduling pipeline, and return the ordered task list."""
        # Reset state for a fresh run
        self.scheduled_tasks = []
        self.skipped_tasks = []
        self.reasoning_log = []

        all_tasks = self._collect_all_tasks()
        sorted_tasks = self._sort_tasks(all_tasks)
        self._fit_within_budget(sorted_tasks)

        return self.scheduled_tasks

    def _collect_all_tasks(self) -> list[Task]:
        """Gather pending tasks from every pet and stamp each with its pet's name."""
        tasks = []
        for pet in self.owner.get_pets():
            for task in pet.get_pending_tasks():
                task.pet_name = pet.name
                tasks.append(task)
        return tasks

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks: fixed-time first by time, then flexible by priority (desc) and duration (asc)."""
        fixed    = sorted(
            [t for t in tasks if t.fixed_time is not None],
            key=lambda t: t.fixed_time,
        )
        flexible = sorted(
            [t for t in tasks if t.fixed_time is None],
            key=lambda t: (-t.priority_score(), t.duration),
        )
        return fixed + flexible

    def _fit_within_budget(self, tasks: list[Task]) -> None:
        """Greedily schedule tasks that fit the remaining time budget; log every decision."""
        remaining = self.time_budget

        for task in tasks:
            label = f"{task.pet_name}: {task.name}" if task.pet_name else task.name
            time_tag = f", fixed @ {task.fixed_time}" if task.fixed_time else ""

            if task.duration <= remaining:
                self.scheduled_tasks.append(task)
                remaining -= task.duration
                self.reasoning_log.append(
                    f"SCHEDULED  {label} "
                    f"({task.duration}min, {task.priority}{time_tag}) — "
                    f"{remaining}min remaining."
                )
            else:
                self.skipped_tasks.append(task)
                self.reasoning_log.append(
                    f"SKIPPED    {label} "
                    f"({task.duration}min needed, only {remaining}min left)."
                )

    def get_summary(self) -> str:
        """Return a human-readable string of the scheduled plan."""
        if not self.scheduled_tasks:
            return f"No tasks scheduled for {self.owner.name}'s pets today."

        time_used = sum(t.duration for t in self.scheduled_tasks)
        lines = [
            f"=== PawPal+ Daily Plan for {self.owner.name} ===",
            f"Time budget: {self.time_budget} min  |  Used: {time_used} min  |  Free: {self.time_budget - time_used} min",
            "",
            "Scheduled:",
        ]
        for i, task in enumerate(self.scheduled_tasks, start=1):
            label = f"{task.pet_name}: {task.name}" if task.pet_name else task.name
            time_tag = f" @ {task.fixed_time}" if task.fixed_time else ""
            lines.append(f"  {i:>2}. {label}  ({task.task_type}, {task.duration}min, {task.priority}{time_tag})")

        if self.skipped_tasks:
            lines.append("\nSkipped (insufficient time):")
            for task in self.skipped_tasks:
                label = f"{task.pet_name}: {task.name}" if task.pet_name else task.name
                lines.append(f"       {label}  ({task.duration}min, {task.priority})")

        return "\n".join(lines)

    def explain(self) -> list[str]:
        """Return the reasoning log produced during generate_plan()."""
        return self.reasoning_log
