"""A minimal Given/When/Then harness.

Context
-------
The specification asks for BDD scenarios.  Rather than add a dependency, this
module gives the three Gherkin keywords real meaning inside plain pytest: each
step is recorded, and if an assertion fails the scenario transcript is attached
to the failure so the report reads like the feature file it mirrors.

Usage::

    def test_find_matches_between_two_teams(graph):
        with Scenario("Find matches between two teams") as s:
            s.given("the match data is loaded", lambda: graph)
            result = s.when("I search for Flamengo vs Fluminense",
                            lambda: head_to_head("Flamengo", "Fluminense"))
            s.then("I receive a list of matches", result["matches"])

The ``.feature`` files under ``tests/features`` are the human-readable
counterpart; every scenario in them has a test of the same name here.
"""

from __future__ import annotations

from typing import Any, Callable


class ScenarioFailed(AssertionError):
    pass


class Scenario:
    """Records Given/When/Then steps and reports them on failure."""

    def __init__(self, name: str):
        self.name = name
        self.steps: list[str] = []

    # -- context manager --------------------------------------------------
    def __enter__(self) -> "Scenario":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None and issubclass(exc_type, AssertionError):
            raise ScenarioFailed(f"{self.transcript()}\n\nFAILED: {exc}") from exc
        return False

    # -- steps ------------------------------------------------------------
    def given(self, description: str, action: Callable[[], Any] | None = None) -> Any:
        return self._step("Given", description, action)

    def when(self, description: str, action: Callable[[], Any] | None = None) -> Any:
        return self._step("When", description, action)

    def then(self, description: str, condition: Any = True) -> Any:
        self.steps.append(f"  Then {description}")
        if callable(condition):
            condition = condition()
        if not condition:
            raise AssertionError(f"Then {description}")
        return condition

    def and_(self, description: str, condition: Any = True) -> Any:
        self.steps.append(f"  And  {description}")
        if callable(condition):
            condition = condition()
        if not condition:
            raise AssertionError(f"And {description}")
        return condition

    def _step(self, keyword: str, description: str,
              action: Callable[[], Any] | None) -> Any:
        self.steps.append(f"  {keyword:<5s} {description}")
        return action() if action is not None else None

    def transcript(self) -> str:
        return f"Scenario: {self.name}\n" + "\n".join(self.steps)
