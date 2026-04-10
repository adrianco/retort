"""State machine for candidate stack lifecycle.

States: candidate → screening → trial → production → retired

Each stack (identified by a string key) progresses through these states.
Transitions are validated against the allowed graph and require passing
the appropriate promotion gate.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from retort.promotion.changelog import record_transition
from retort.promotion.gates import GateResult


class LifecycleState(str, enum.Enum):
    candidate = "candidate"
    screening = "screening"
    trial = "trial"
    production = "production"
    retired = "retired"


# Allowed forward transitions.
TRANSITIONS: dict[LifecycleState, LifecycleState] = {
    LifecycleState.candidate: LifecycleState.screening,
    LifecycleState.screening: LifecycleState.trial,
    LifecycleState.trial: LifecycleState.production,
    LifecycleState.production: LifecycleState.retired,
}

# Map transition edges to the config gate name used in PromotionConfig.
TRANSITION_GATE_NAMES: dict[tuple[LifecycleState, LifecycleState], str | None] = {
    (LifecycleState.candidate, LifecycleState.screening): None,  # automatic
    (LifecycleState.screening, LifecycleState.trial): "screening_to_trial",
    (LifecycleState.trial, LifecycleState.production): "trial_to_production",
    (LifecycleState.production, LifecycleState.retired): "production_to_retired",
}


class InvalidTransition(Exception):
    """Raised when a lifecycle transition is not allowed."""


@dataclass
class StackLifecycle:
    """Tracks lifecycle state for a collection of stacks.

    Parameters
    ----------
    changelog:
        Mutable list that receives :class:`~retort.promotion.changelog.ChangelogEntry`
        objects for every successful transition.
    """

    _states: dict[str, LifecycleState] = field(default_factory=dict)
    changelog: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, stack_id: str) -> LifecycleState:
        """Register a new stack as a *candidate*.

        Raises ``ValueError`` if the stack is already registered.
        """
        if stack_id in self._states:
            raise ValueError(f"stack {stack_id!r} is already registered")
        self._states[stack_id] = LifecycleState.candidate
        record_transition(
            self.changelog,
            stack_id=stack_id,
            from_state=None,
            to_state=LifecycleState.candidate,
            gate_result=None,
            reason="initial registration",
        )
        return LifecycleState.candidate

    def state(self, stack_id: str) -> LifecycleState:
        """Return the current state of *stack_id*.

        Raises ``KeyError`` if the stack is not registered.
        """
        try:
            return self._states[stack_id]
        except KeyError:
            raise KeyError(f"stack {stack_id!r} is not registered") from None

    def promote(
        self,
        stack_id: str,
        gate_result: GateResult,
        *,
        reason: str = "",
    ) -> LifecycleState:
        """Advance *stack_id* to the next lifecycle state.

        The gate must have ``passed=True`` (except for candidate→screening
        which is automatic — pass any gate result or ``None``-equivalent).

        Returns the new state on success.

        Raises
        ------
        KeyError
            If *stack_id* is not registered.
        InvalidTransition
            If the stack is in a terminal state or the gate did not pass.
        """
        current = self.state(stack_id)

        if current not in TRANSITIONS:
            raise InvalidTransition(
                f"stack {stack_id!r} is in terminal state {current.value!r}"
            )

        target = TRANSITIONS[current]
        gate_name = TRANSITION_GATE_NAMES.get((current, target))

        # candidate→screening is automatic (no gate required).
        if gate_name is not None and not gate_result.passed:
            raise InvalidTransition(
                f"gate {gate_name!r} did not pass for {stack_id!r}: "
                f"{gate_result.detail}"
            )

        self._states[stack_id] = target
        record_transition(
            self.changelog,
            stack_id=stack_id,
            from_state=current,
            to_state=target,
            gate_result=gate_result,
            reason=reason,
        )
        return target

    @property
    def stacks(self) -> dict[str, LifecycleState]:
        """Return a snapshot of all stacks and their current states."""
        return dict(self._states)

    def stacks_in(self, state: LifecycleState) -> list[str]:
        """Return stack IDs currently in the given *state*."""
        return [sid for sid, s in self._states.items() if s is state]
