"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic

Run:  python -m pytest
"""

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
