"""Candidate intake — watch for new factor levels and trigger augmentation.

When a new candidate appears (e.g., a new AI agent ships, a new framework
releases), the intake module:

1. Registers the new level with the factor registry.
2. Triggers D-optimal augmentation to extend the existing design matrix.
3. Registers the new candidate in the lifecycle state machine.
4. Returns the augmentation rows that need to be scheduled for execution.

The candidate enters at the ``candidate`` lifecycle phase and is automatically
promoted to ``screening`` once augmentation rows are generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from retort.design.augmentor import AugmentationResult, augment_design
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignMatrix, DesignPhase
from retort.promotion.gates import GateResult
from retort.promotion.lifecycle import StackLifecycle


@dataclass(frozen=True)
class IntakeResult:
    """Result of ingesting a new candidate.

    Attributes:
        factor_name: The factor that gained a new level.
        new_level: The new level value.
        stack_id: Lifecycle identifier for the new candidate.
        augmentation: D-optimal augmentation result with new runs.
        lifecycle_state: The lifecycle state after intake (screening).
    """

    factor_name: str
    new_level: str
    stack_id: str
    augmentation: AugmentationResult
    lifecycle_state: str

    @property
    def num_new_runs(self) -> int:
        return self.augmentation.num_new_runs

    @property
    def new_rows(self) -> pd.DataFrame:
        return self.augmentation.new_rows


def _build_stack_id(factor_name: str, level: str) -> str:
    """Build a lifecycle stack ID from factor name and level.

    Convention: ``factor_name:level`` (e.g., ``agent:new-agent-v1``).
    """
    return f"{factor_name}:{level}"


def intake_candidate(
    factor_name: str,
    new_level: str,
    registry: FactorRegistry,
    existing_design: DesignMatrix,
    lifecycle: StackLifecycle | None = None,
    *,
    nrestarts: int = 40,
    n_runs: int | None = None,
) -> IntakeResult:
    """Ingest a new candidate into the experiment system.

    This is the main entry point for the intake subsystem.  It:
    1. Validates that the factor exists and the level is genuinely new.
    2. Triggers D-optimal augmentation.
    3. Optionally registers the candidate in the lifecycle state machine
       and auto-promotes to screening.

    Args:
        factor_name: Which factor is gaining a new level (e.g. ``"agent"``).
        new_level: The new level value (e.g. ``"new-agent-v1"``).
        registry: Current factor registry (*before* the new level).
        existing_design: The current design matrix.
        lifecycle: Optional lifecycle tracker.  If provided, the candidate is
            registered and auto-promoted to screening.
        nrestarts: Optimizer restarts for D-optimal generation.
        n_runs: Override total run count for the augmented design.

    Returns:
        IntakeResult describing the new candidate and augmentation rows.

    Raises:
        ValueError: If the factor doesn't exist or level already exists.
    """
    # D-optimal augmentation
    augmentation = augment_design(
        existing=existing_design,
        registry=registry,
        factor_name=factor_name,
        new_level=new_level,
        nrestarts=nrestarts,
        n_runs=n_runs,
    )

    stack_id = _build_stack_id(factor_name, new_level)
    lifecycle_state = "candidate"

    if lifecycle is not None:
        lifecycle.register(stack_id)
        # Auto-promote candidate → screening (this transition is automatic)
        auto_gate = GateResult(
            passed=True,
            gate_name="candidate_to_screening",
            detail="auto-promote on intake",
        )
        lifecycle.promote(
            stack_id,
            auto_gate,
            reason=f"intake: new level {new_level!r} for factor {factor_name!r}",
        )
        lifecycle_state = lifecycle.state(stack_id).value

    return IntakeResult(
        factor_name=factor_name,
        new_level=new_level,
        stack_id=stack_id,
        augmentation=augmentation,
        lifecycle_state=lifecycle_state,
    )


def load_existing_design(
    config_path: str | Path,
    phase: str = "screening",
) -> tuple[FactorRegistry, DesignMatrix]:
    """Load factor registry and generate current design from a workspace config.

    Convenience wrapper that reads a workspace YAML and generates the design
    matrix for the given phase.  Used by the CLI to bootstrap intake.

    Args:
        config_path: Path to ``workspace.yaml``.
        phase: Design phase (``"screening"`` or ``"characterization"``).

    Returns:
        Tuple of (registry, design_matrix).
    """
    import yaml

    from retort.design.generator import generate_design

    with open(config_path) as f:
        data = yaml.safe_load(f)

    factors_spec = data.get("factors", {})
    if not factors_spec:
        raise ValueError(f"No 'factors' key found in {config_path}")

    registry = FactorRegistry()
    for name, spec in factors_spec.items():
        levels = spec if isinstance(spec, list) else spec.get("levels", [])
        registry.add(name, levels)

    design = generate_design(registry, phase)
    return registry, design
