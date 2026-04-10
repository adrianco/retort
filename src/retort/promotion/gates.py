"""Configurable promotion gates.

Each gate evaluates a statistical evidence dict against configured thresholds
and returns a :class:`GateResult` indicating pass/fail with a human-readable
detail message.
"""

from __future__ import annotations

from dataclasses import dataclass

from retort.config.schema import PromotionConfig, PromotionGate


@dataclass(frozen=True)
class GateResult:
    """Outcome of a gate evaluation."""

    passed: bool
    gate_name: str
    detail: str


def evaluate_gate(
    gate_name: str,
    evidence: dict[str, float],
    config: PromotionConfig,
) -> GateResult:
    """Evaluate *evidence* against the gate defined by *gate_name*.

    Parameters
    ----------
    gate_name:
        One of ``"screening_to_trial"``, ``"trial_to_production"``,
        ``"production_to_retired"``.
    evidence:
        Mapping of metric names to observed values.  Expected keys depend on
        the gate:

        * ``screening_to_trial`` — requires ``"p_value"``
        * ``trial_to_production`` — requires ``"posterior_confidence"``
        * ``production_to_retired`` — requires ``"dominated_confidence"``
    config:
        The workspace :class:`PromotionConfig` containing threshold values.

    Returns
    -------
    GateResult
        With ``passed=True`` if all configured thresholds are met.
    """
    gate: PromotionGate = getattr(config, gate_name, None)
    if gate is None:
        return GateResult(
            passed=False,
            gate_name=gate_name,
            detail=f"unknown gate {gate_name!r}",
        )

    checks: list[str] = []
    all_passed = True

    if gate.p_value is not None:
        observed = evidence.get("p_value")
        if observed is None:
            all_passed = False
            checks.append("p_value: missing from evidence")
        elif observed > gate.p_value:
            all_passed = False
            checks.append(
                f"p_value: {observed:.4f} > threshold {gate.p_value:.4f}"
            )
        else:
            checks.append(
                f"p_value: {observed:.4f} <= threshold {gate.p_value:.4f} ✓"
            )

    if gate.posterior_confidence is not None:
        observed = evidence.get("posterior_confidence")
        if observed is None:
            all_passed = False
            checks.append("posterior_confidence: missing from evidence")
        elif observed < gate.posterior_confidence:
            all_passed = False
            checks.append(
                f"posterior_confidence: {observed:.4f} < threshold "
                f"{gate.posterior_confidence:.4f}"
            )
        else:
            checks.append(
                f"posterior_confidence: {observed:.4f} >= threshold "
                f"{gate.posterior_confidence:.4f} ✓"
            )

    if gate.dominated_confidence is not None:
        observed = evidence.get("dominated_confidence")
        if observed is None:
            all_passed = False
            checks.append("dominated_confidence: missing from evidence")
        elif observed < gate.dominated_confidence:
            all_passed = False
            checks.append(
                f"dominated_confidence: {observed:.4f} < threshold "
                f"{gate.dominated_confidence:.4f}"
            )
        else:
            checks.append(
                f"dominated_confidence: {observed:.4f} >= threshold "
                f"{gate.dominated_confidence:.4f} ✓"
            )

    # If no thresholds are configured, the gate passes vacuously.
    if not checks:
        checks.append("no thresholds configured — gate passes vacuously")

    detail = "; ".join(checks)
    return GateResult(passed=all_passed, gate_name=gate_name, detail=detail)
