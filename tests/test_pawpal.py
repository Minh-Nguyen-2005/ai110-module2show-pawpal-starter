"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic

Run:  python -m pytest
"""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Helpers — reusable fixtures built as plain functions (no pytest dependency)
# ---------------------------------------------------------------------------

def make_task(**kwargs) -> Task:
    """Return a Task with sensible defaults; override any field via kwargs."""
    defaults = dict(name="Test task", task_type="walk", duration=20, priority="medium")
    defaults.update(kwargs)
    return Task(**defaults)


def make_pet_with_tasks(n: int = 0) -> Pet:
    """Return a Pet pre-loaded with n tasks."""
    pet = Pet("Buddy", species="dog", age=2)
    for i in range(n):
        pet.add_task(make_task(name=f"Task {i + 1}"))
    return pet


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTask:

    def test_mark_complete_changes_status(self):
        """mark_complete() must flip is_completed from False to True."""
        task = make_task()

        assert task.is_completed is False, "Task should start incomplete"
        task.mark_complete()
        assert task.is_completed is True, "Task should be complete after mark_complete()"

    def test_mark_complete_is_idempotent(self):
        """Calling mark_complete() twice should not raise or change anything."""
        task = make_task()
        task.mark_complete()
        task.mark_complete()
        assert task.is_completed is True

    def test_priority_score_values(self):
        """priority_score() must return 3 / 2 / 1 for high / medium / low."""
        assert make_task(priority="high").priority_score()   == 3
        assert make_task(priority="medium").priority_score() == 2
        assert make_task(priority="low").priority_score()    == 1


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPet:

    def test_add_task_increases_count(self):
        """add_task() must increase the pet's task count by one."""
        pet = make_pet_with_tasks(0)

        assert len(pet.get_tasks()) == 0
        pet.add_task(make_task(name="Morning walk"))
        assert len(pet.get_tasks()) == 1

    def test_add_multiple_tasks_increases_count(self):
        """Each call to add_task() should increment the count."""
        pet = make_pet_with_tasks(0)
        for i in range(3):
            pet.add_task(make_task(name=f"Task {i}"))
        assert len(pet.get_tasks()) == 3

    def test_get_pending_tasks_excludes_completed(self):
        """get_pending_tasks() must not include tasks that are already done."""
        pet = make_pet_with_tasks(0)
        done_task = make_task(name="Done task")
        pending_task = make_task(name="Pending task")

        done_task.mark_complete()
        pet.add_task(done_task)
        pet.add_task(pending_task)

        pending = pet.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0].name == "Pending task"

    def test_remove_task_by_name(self):
        """remove_task() must remove exactly the named task."""
        pet = make_pet_with_tasks(0)
        pet.add_task(make_task(name="Walk"))
        pet.add_task(make_task(name="Feed"))

        pet.remove_task("Walk")
        names = [t.name for t in pet.get_tasks()]
        assert "Walk" not in names
        assert "Feed" in names


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:

    def _make_owner(self, budget: int = 60) -> Owner:
        return Owner("Test owner", daily_time_budget=budget)

    def test_high_priority_scheduled_before_low(self):
        """High-priority tasks must appear before low-priority ones in the plan."""
        owner = self._make_owner(budget=60)
        pet = Pet("Rex", "dog", 1)
        pet.add_task(make_task(name="Low task",  priority="low",  duration=10))
        pet.add_task(make_task(name="High task", priority="high", duration=10))
        owner.add_pet(pet)

        plan = Scheduler(owner).generate_plan()
        names = [t.name for t in plan]
        assert names.index("High task") < names.index("Low task")

    def test_fixed_time_task_scheduled_first(self):
        """A fixed-time task must appear before flexible tasks of any priority."""
        owner = self._make_owner(budget=60)
        pet = Pet("Rex", "dog", 1)
        pet.add_task(make_task(name="Flexible high", priority="high",  duration=10))
        pet.add_task(make_task(name="Fixed med",     priority="medium", duration=10, fixed_time="08:00"))
        owner.add_pet(pet)

        plan = Scheduler(owner).generate_plan()
        names = [t.name for t in plan]
        assert names.index("Fixed med") < names.index("Flexible high")

    def test_tasks_exceeding_budget_are_skipped(self):
        """Tasks that don't fit in the remaining budget must land in skipped_tasks."""
        owner = self._make_owner(budget=20)
        pet = Pet("Rex", "dog", 1)
        pet.add_task(make_task(name="Short", priority="high", duration=10))
        pet.add_task(make_task(name="Long",  priority="low",  duration=30))
        owner.add_pet(pet)

        s = Scheduler(owner)
        s.generate_plan()
        assert any(t.name == "Long" for t in s.skipped_tasks)
        assert any(t.name == "Short" for t in s.scheduled_tasks)

    def test_empty_owner_produces_empty_plan(self):
        """An owner with no pets must produce an empty scheduled list."""
        owner = self._make_owner()
        plan = Scheduler(owner).generate_plan()
        assert plan == []

    def test_reasoning_log_has_entry_per_task(self):
        """The reasoning log must contain one entry for every task processed."""
        owner = self._make_owner(budget=60)
        pet = Pet("Rex", "dog", 1)
        pet.add_task(make_task(name="A", duration=10))
        pet.add_task(make_task(name="B", duration=10))
        owner.add_pet(pet)

        s = Scheduler(owner)
        s.generate_plan()
        assert len(s.reasoning_log) == 2


# ---------------------------------------------------------------------------
# Sort-by-time tests
# ---------------------------------------------------------------------------

class TestSortByTime:
    """
    sort_by_time() must use datetime.time comparison, not string comparison.

    The critical bug it fixes: under plain string sort, "9:00" > "10:00"
    because Python compares character by character and "9" > "1".
    Using datetime.time(9, 0) < datetime.time(10, 0) gives the correct result.
    """

    def test_fixed_times_sorted_in_clock_order(self):
        """Tasks with different fixed times must appear earliest-first."""
        s = _make_scheduler()
        tasks = [
            make_task(name="10am task", fixed_time="10:00"),
            make_task(name="7am task",  fixed_time="07:00"),
            make_task(name="9am task",  fixed_time="09:00"),
        ]
        result = s.sort_by_time(tasks)
        names = [t.name for t in result]
        assert names == ["7am task", "9am task", "10am task"]

    def test_single_digit_hour_sorts_before_double_digit(self):
        """
        '9:00' must sort BEFORE '10:00' — the exact bug string sort gets wrong.

        String sort: '9:00' > '10:00' because ord('9') > ord('1').
        datetime.time sort: time(9,0) < time(10,0) — correct.
        This test would FAIL if the implementation regressed to raw string sort.
        """
        s = _make_scheduler()
        tasks = [
            make_task(name="10am", fixed_time="10:00"),
            make_task(name="9am",  fixed_time="9:00"),
        ]
        result = s.sort_by_time(tasks)
        assert result[0].name == "9am",  "9:00 must come before 10:00"
        assert result[1].name == "10am"

    def test_flexible_tasks_sorted_after_all_fixed_tasks(self):
        """Tasks without a fixed_time must appear after every fixed-time task."""
        s = _make_scheduler()
        tasks = [
            make_task(name="Flexible",   fixed_time=None),
            make_task(name="Fixed late", fixed_time="23:00"),
            make_task(name="Fixed early", fixed_time="06:00"),
        ]
        result = s.sort_by_time(tasks)
        fixed_indices    = [i for i, t in enumerate(result) if t.fixed_time]
        flexible_indices = [i for i, t in enumerate(result) if not t.fixed_time]
        assert max(fixed_indices) < min(flexible_indices)

    def test_empty_list_returns_empty(self):
        """sort_by_time on an empty list must return an empty list without error."""
        assert _make_scheduler().sort_by_time([]) == []


def _make_scheduler() -> Scheduler:
    """Module-level helper — creates a minimal Scheduler for sort_by_time tests."""
    return Scheduler(Owner("Test", daily_time_budget=120))


# ---------------------------------------------------------------------------
# Recurring task tests
# ---------------------------------------------------------------------------

class TestRecurringTasks:
    """
    date arithmetic explanation:
        date(2026, 4, 6) + timedelta(days=1)  → date(2026, 4, 7)
        date(2026, 4, 6) + timedelta(weeks=1) → date(2026, 4, 13)

    timedelta handles month/year rollovers automatically, e.g.
        date(2026, 1, 31) + timedelta(days=1) → date(2026, 2, 1)
    """

    TODAY = date(2026, 4, 6)   # pinned so tests never depend on the real clock

    def test_daily_task_creates_next_occurrence_plus_one_day(self):
        """Completing a daily task must produce a new task due tomorrow."""
        task = make_task(name="Feed", frequency="daily", due_date=self.TODAY)
        next_task = task.next_occurrence(today=self.TODAY)

        assert next_task is not None
        assert next_task.due_date == self.TODAY + timedelta(days=1)

    def test_weekly_task_creates_next_occurrence_plus_seven_days(self):
        """Completing a weekly task must produce a new task due in 7 days."""
        task = make_task(name="Brush", frequency="weekly", due_date=self.TODAY)
        next_task = task.next_occurrence(today=self.TODAY)

        assert next_task is not None
        assert next_task.due_date == self.TODAY + timedelta(weeks=1)

    def test_once_task_produces_no_next_occurrence(self):
        """A 'once' task must return None from next_occurrence — never duplicated."""
        task = make_task(name="Vet visit", frequency="once", due_date=self.TODAY)
        assert task.next_occurrence(today=self.TODAY) is None

    def test_complete_task_appends_recurrence_to_pet(self):
        """
        Pet.complete_task() must:
          1. Mark the original task complete.
          2. Append the next occurrence to pet.tasks (so count goes from 1 → 2).
        """
        pet = Pet("Buddy", "dog", 2)
        pet.add_task(make_task(name="Daily walk", frequency="daily", due_date=self.TODAY))

        assert len(pet.get_tasks()) == 1
        pet.complete_task("Daily walk", today=self.TODAY)
        assert len(pet.get_tasks()) == 2                          # original + next occurrence

        original, next_task = pet.get_tasks()
        assert original.is_completed is True
        assert next_task.due_date == self.TODAY + timedelta(days=1)

    def test_complete_once_task_does_not_grow_task_list(self):
        """Completing a 'once' task must leave the task list length unchanged."""
        pet = Pet("Buddy", "dog", 2)
        pet.add_task(make_task(name="Vet visit", frequency="once", due_date=self.TODAY))

        pet.complete_task("Vet visit", today=self.TODAY)
        assert len(pet.get_tasks()) == 1    # no new task appended

    def test_future_due_date_excluded_from_pending_today(self):
        """
        A task due tomorrow must not appear in get_pending_tasks(today=TODAY).

        This is what makes recurring tasks safe: completing a daily task
        auto-appends tomorrow's instance, but that instance should be invisible
        until tomorrow's plan runs.
        """
        pet = Pet("Buddy", "dog", 2)
        tomorrow = self.TODAY + timedelta(days=1)
        pet.add_task(make_task(name="Future task", due_date=tomorrow))
        pet.add_task(make_task(name="Due today",   due_date=self.TODAY))

        pending = pet.get_pending_tasks(today=self.TODAY)
        names = [t.name for t in pending]
        assert "Future task" not in names
        assert "Due today" in names

    def test_overdue_task_is_included_in_pending(self):
        """A task whose due_date is in the past must still appear as pending."""
        pet = Pet("Buddy", "dog", 2)
        yesterday = self.TODAY - timedelta(days=1)
        pet.add_task(make_task(name="Overdue", due_date=yesterday))

        pending = pet.get_pending_tasks(today=self.TODAY)
        assert any(t.name == "Overdue" for t in pending)

    def test_next_occurrence_is_not_completed(self):
        """The newly created recurrence task must start with is_completed=False."""
        task = make_task(name="Meds", frequency="daily", due_date=self.TODAY)
        task.mark_complete()
        next_task = task.next_occurrence(today=self.TODAY)

        assert next_task is not None
        assert next_task.is_completed is False


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """
    Overlap rule:  two windows [start_a, end_a) and [start_b, end_b) overlap
    when  start_a < end_b  AND  start_b < end_a.

    The strict inequalities mean adjacent tasks (end_a == start_b) do NOT
    conflict — a task finishing at 09:00 and one starting at 09:00 can both
    be scheduled without a clash.
    """

    def _make_owner_with_tasks(self, *task_args) -> Owner:
        """Build a single-pet owner loaded with tasks given as keyword dicts."""
        owner = Owner("Test", daily_time_budget=240)
        pet = Pet("Rex", "dog", 1)
        for kwargs in task_args:
            pet.add_task(make_task(**kwargs))
        owner.add_pet(pet)
        return owner

    def test_same_start_time_flagged_as_conflict(self):
        """Two tasks with identical fixed times must produce at least one conflict."""
        owner = self._make_owner_with_tasks(
            dict(name="Task A", fixed_time="08:00", duration=15),
            dict(name="Task B", fixed_time="08:00", duration=10),
        )
        s = Scheduler(owner)
        s.generate_plan()
        assert len(s.conflicts) == 1
        assert "Task A" in s.conflicts[0]
        assert "Task B" in s.conflicts[0]

    def test_overlapping_windows_flagged(self):
        """
        A task at 07:50 (20 min) ends at 08:10.
        A task at 08:00 (30 min) starts at 08:00.
        Their windows overlap from 08:00 to 08:10 → must be flagged.
        """
        owner = self._make_owner_with_tasks(
            dict(name="Early",  fixed_time="07:50", duration=20),
            dict(name="Later",  fixed_time="08:00", duration=30),
        )
        s = Scheduler(owner)
        s.generate_plan()
        assert len(s.conflicts) == 1

    def test_adjacent_tasks_not_flagged(self):
        """
        Task A ends at exactly 09:00; Task B starts at exactly 09:00.
        end_a == start_b means start_b < end_a is FALSE → no overlap → no conflict.
        """
        owner = self._make_owner_with_tasks(
            dict(name="Walk",  fixed_time="08:30", duration=30),   # ends 09:00
            dict(name="Meds",  fixed_time="09:00", duration=10),   # starts 09:00
        )
        s = Scheduler(owner)
        s.generate_plan()
        assert s.conflicts == []

    def test_no_fixed_time_tasks_produce_no_conflicts(self):
        """Flexible tasks (no fixed_time) can never conflict — only fixed ones can."""
        owner = self._make_owner_with_tasks(
            dict(name="Walk",   fixed_time=None, duration=30),
            dict(name="Groom",  fixed_time=None, duration=20),
        )
        s = Scheduler(owner)
        s.generate_plan()
        assert s.conflicts == []

    def test_non_overlapping_fixed_tasks_produce_no_conflicts(self):
        """Tasks at 07:00 (10 min) and 08:00 (10 min) have a 50-minute gap — no conflict."""
        owner = self._make_owner_with_tasks(
            dict(name="Breakfast", fixed_time="07:00", duration=10),
            dict(name="Meds",      fixed_time="08:00", duration=10),
        )
        s = Scheduler(owner)
        s.generate_plan()
        assert s.conflicts == []

    def test_conflict_does_not_prevent_scheduling(self):
        """Conflicts are warnings only — the schedule must still be generated."""
        owner = self._make_owner_with_tasks(
            dict(name="Task A", fixed_time="08:00", duration=15, priority="high"),
            dict(name="Task B", fixed_time="08:00", duration=10, priority="high"),
        )
        s = Scheduler(owner)
        s.generate_plan()
        # Conflicts flagged AND plan still produced
        assert len(s.conflicts) > 0
        assert len(s.scheduled_tasks) > 0


# ---------------------------------------------------------------------------
# Filtering tests
# ---------------------------------------------------------------------------

class TestFiltering:

    def _make_owner(self) -> Owner:
        owner = Owner("Sam", daily_time_budget=120)
        dog = Pet("Rex",  "dog", 3)
        cat = Pet("Luna", "cat", 2)
        dog.add_task(make_task(name="Walk",    priority="high"))
        dog.add_task(make_task(name="Feed dog", priority="medium"))
        cat.add_task(make_task(name="Feed cat", priority="high"))
        cat.add_task(make_task(name="Play",     priority="low"))
        cat.get_tasks()[0].mark_complete()   # mark "Feed cat" done
        owner.add_pet(dog)
        owner.add_pet(cat)
        return owner

    def test_filter_by_pet_name_returns_only_that_pets_tasks(self):
        """get_all_tasks(pet_name='Rex') must include only Rex's tasks."""
        owner = self._make_owner()
        tasks = owner.get_all_tasks(pet_name="Rex")
        assert all(t.name in {"Walk", "Feed dog"} for t in tasks)
        assert len(tasks) == 2

    def test_filter_by_completed_false_returns_only_pending(self):
        """get_all_tasks(completed=False) must exclude any completed tasks."""
        owner = self._make_owner()
        pending = owner.get_all_tasks(completed=False)
        assert all(not t.is_completed for t in pending)
        # "Feed cat" was marked done, so it must not appear
        assert not any(t.name == "Feed cat" for t in pending)

    def test_filter_by_nonexistent_pet_returns_empty(self):
        """Filtering by a pet name that doesn't exist must return [] without error."""
        owner = self._make_owner()
        assert owner.get_all_tasks(pet_name="Ghost") == []

    def test_no_filters_returns_all_tasks(self):
        """get_all_tasks() with no arguments must return every task from every pet."""
        owner = self._make_owner()
        assert len(owner.get_all_tasks()) == 4
