"""Retort's own metaharness config: model + effort per internal role.

Pinned roles (experiment, evaluator) are never routed. Routed roles use the
metaharness cost-aware rule: the cheapest tier whose measured quality clears
``quality_bar``; with no evidence, the configured static tier.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "metaharness.yaml"


class MetaharnessConfigError(ValueError):
    pass


@dataclass(frozen=True)
class RoleSpec:
    role: str
    model: str  # "" => taken from the design factors (experiment)
    effort: str
    pinned: bool
    source: str  # pin | tier:<name> | routed:<name>

    def cli_args(self) -> list[str]:
        from retort.playpen.local_runner import _effort_cli_args, _model_cli_args
        return [*_model_cli_args(self.model), *_effort_cli_args(self.effort)]

    def as_record(self) -> dict[str, Any]:
        return {"model": self.model, "effort": self.effort,
                "pinned": self.pinned, "source": self.source}


def load(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_PATH
    try:
        cfg = yaml.safe_load(p.read_text())
    except OSError as exc:
        raise MetaharnessConfigError(f"cannot read {p}: {exc}") from exc
    _validate(cfg)
    return cfg


def _validate(cfg: Any) -> None:
    from retort.playpen.local_runner import EFFORT_LEVELS
    if not isinstance(cfg, dict) or cfg.get("version") != 1:
        raise MetaharnessConfigError("metaharness config must be a mapping with version: 1")
    for name in ("experiment", "evaluator"):
        if name not in (cfg.get("pinned") or {}):
            raise MetaharnessConfigError(f"pinned.{name} is required")
    esc = cfg.get("escalation") or {}
    rungs = esc.get("ladder") or []
    prices = cfg.get("prices") or {}
    if not rungs or any(r not in cfg.get("tiers", {}) or r not in prices for r in rungs):
        raise MetaharnessConfigError("escalation.ladder must list tiers that have a tier and a price")
    if [prices[r] for r in rungs] != sorted(prices[r] for r in rungs):
        raise MetaharnessConfigError("escalation.ladder must be ascending in price")
    if not 0 <= esc.get("min_confidence", 0.7) <= 1:
        raise MetaharnessConfigError("escalation.min_confidence must be in [0,1]")
    for role, r in (cfg.get("routed", {}).get("roles") or {}).items():
        for k in ("start", "ceiling"):
            if r.get(k, rungs[0]) not in rungs:
                raise MetaharnessConfigError(f"role {role!r}: {k} not on the ladder")
        if rungs.index(r.get("start", rungs[0])) > rungs.index(r.get("ceiling", rungs[-1])):
            raise MetaharnessConfigError(f"role {role!r}: start above ceiling")
    ev = cfg["pinned"]["evaluator"]
    if not ev.get("model"):
        raise MetaharnessConfigError("pinned.evaluator.model is required")
    tiers = cfg.get("tiers") or {}
    for tname, t in tiers.items():
        if t.get("effort") not in EFFORT_LEVELS or not t.get("model"):
            raise MetaharnessConfigError(f"tier {tname!r}: needs model and effort in {EFFORT_LEVELS}")
    if ev.get("effort", "default") not in EFFORT_LEVELS:
        raise MetaharnessConfigError("pinned.evaluator.effort invalid")
    for role, r in (cfg.get("routed", {}).get("roles") or {}).items():
        if r.get("tier") not in tiers:
            raise MetaharnessConfigError(f"role {role!r}: unknown tier {r.get('tier')!r}")
        if role in cfg["pinned"]:
            raise MetaharnessConfigError(f"role {role!r} is both pinned and routed")


def route_tier(quality: dict[str, float], prices: dict[str, float], bar: float) -> str | None:
    """Cheapest tier whose measured quality >= bar; None if none qualifies."""
    ok = [t for t, q in quality.items() if q >= bar and t in prices]
    return min(ok, key=lambda t: prices[t]) if ok else None


def resolve(role: str, cfg: dict[str, Any] | None = None,
            quality: dict[str, float] | None = None) -> RoleSpec:
    """Resolve a role to model+effort. ``quality`` ({tier: score}) is optional
    routing evidence; it is ignored (and refused) for pinned roles."""
    cfg = cfg or load()
    pinned = cfg["pinned"]
    if role in pinned:
        if quality is not None:
            raise MetaharnessConfigError(f"role {role!r} is pinned and cannot be routed")
        p = pinned[role]
        return RoleSpec(role, p.get("model", ""), p.get("effort", "default"), True, "pin")
    spec = (cfg["routed"].get("roles") or {}).get(role)
    if spec is None:
        raise MetaharnessConfigError(f"unknown role {role!r}")
    tier, source = spec["tier"], f"tier:{spec['tier']}"
    if quality:
        picked = route_tier(quality, cfg.get("prices", {}), cfg["routed"].get("quality_bar", 0.9))
        if picked:
            tier, source = picked, f"routed:{picked}"
    t = cfg["tiers"][tier]
    return RoleSpec(role, t["model"], t["effort"], False, source)


def ladder(role: str, cfg: dict[str, Any] | None = None) -> list[str]:
    """Rungs this role may use, lowest first: ``start`` .. ``ceiling`` of the ladder."""
    cfg = cfg or load()
    if role in cfg["pinned"]:
        return []  # pinned roles never escalate
    rungs = cfg["escalation"]["ladder"]
    spec = cfg["routed"]["roles"][role]
    lo = rungs.index(spec.get("start", rungs[0]))
    hi = rungs.index(spec.get("ceiling", rungs[-1]))
    return rungs[lo:hi + 1]


def next_tier(role: str, current: str, *, confidence: float | None = None,
              valid: bool = True, cfg: dict[str, Any] | None = None) -> str | None:
    """Metaharness-style escalation: the next rung, or None to stop.

    Escalates only when the pass was unconvincing (confidence below the floor, or its
    output invalid); a convincing pass stops. None also at the role's ceiling."""
    cfg = cfg or load()
    esc = cfg["escalation"]
    rungs = ladder(role, cfg)
    if current not in rungs:
        raise MetaharnessConfigError(f"tier {current!r} is not on {role!r}'s ladder {rungs}")
    unconvincing = (confidence is not None and confidence < esc["min_confidence"]) or \
                   (not valid and esc.get("escalate_on_invalid", True))
    i = rungs.index(current)
    return rungs[i + 1] if unconvincing and i + 1 < len(rungs) else None


def spec_for_tier(role: str, tier: str, cfg: dict[str, Any] | None = None) -> RoleSpec:
    cfg = cfg or load()
    if tier not in ladder(role, cfg):
        raise MetaharnessConfigError(f"tier {tier!r} is outside {role!r}'s ladder")
    t = cfg["tiers"][tier]
    return RoleSpec(role, t["model"], t["effort"], False, f"escalate:{tier}")


def snapshot(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every role's effective config -- for provenance.json."""
    cfg = cfg or load()
    roles = [*cfg["pinned"], *cfg["routed"]["roles"]]
    return {r: resolve(r, cfg).as_record() for r in roles}
