"""Factor model — our factors as first-class Retort DoE factors.

Retort's thesis is "vary the whole stack, not just the model". This module
makes the *agentic-orchestration* axis first-class: the harness configuration
(routing / memory / evolved genome / self-consistency), the reasoning scaffold,
and the model all become DoE factors that the screening design crosses with
language and task.

Every level is documented below so the design matrix is self-describing and the
ANOVA effects table reads in plain English.

The output is always a ``retort.design.factors.FactorRegistry`` so the rest of
the Retort machinery (design generator, aliasing inspector, ANOVA) consumes it
unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from retort.design.factors import FactorRegistry, FactorType

# --------------------------------------------------------------------------
# Factor names (stable identifiers used as DataFrame columns + ANOVA terms)
# --------------------------------------------------------------------------
F_MODEL = "model"
F_HARNESS = "harness_config"
F_SCAFFOLD = "scaffold"
F_LANGUAGE = "language"
F_TASK = "task"

# Factors whose levels have a meaningful order (used for ordinal encoding /
# trend reporting). harness_config and scaffold are deliberately CATEGORICAL —
# they are qualitatively different strategies, not a single ordered dial.
ORDINAL_FACTORS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Level:
    """A documented factor level.

    Attributes:
        id: The level identifier used in the design matrix / ANOVA.
        doc: Human-readable description of what this level means / does.
        openrouter: For model levels, the OpenRouter model id used by the
            runner. Empty for non-model factors.
        runner_flags: For harness/scaffold levels, the per-cell flags the
            metaharness runner should be invoked with. The runner glue
            (runner.py) consumes these. Empty for model/language/task.
    """

    id: str
    doc: str
    openrouter: str = ""
    runner_flags: Mapping[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# MODEL — the raw model. Retort finds the model mostly governs spec-reliability.
# Levels chosen to span a cheap-CN / open / frontier / gpt-5.x spread so the
# ANOVA can separate "model effect" from "harness effect".
# --------------------------------------------------------------------------
MODEL_LEVELS: tuple[Level, ...] = (
    Level(
        "deepseek-v4-pro",
        "Cheap high-capability CN model. Our cheap↔frontier baseline.",
        openrouter="deepseek/deepseek-v4-pro",
    ),
    Level(
        "glm-5.2",
        "Z.ai GLM-5.2 — strong cheap CN model, good tool-use.",
        openrouter="z-ai/glm-5.2",
    ),
    Level(
        "opus-4.8",
        "Anthropic Claude Opus 4.8 — frontier reference.",
        openrouter="anthropic/claude-opus-4.8",
    ),
    Level(
        "gpt-5.2",
        "OpenAI GPT-5.2 — a gpt-5.x frontier comparator.",
        openrouter="openai/gpt-5.2",
    ),
)

# --------------------------------------------------------------------------
# HARNESS_CONFIG — the agentic-orchestration axis. This is the headline factor:
# the ANOVA attributes how much of any lift is harnessing vs the raw model.
# --------------------------------------------------------------------------
HARNESS_LEVELS: tuple[Level, ...] = (
    Level(
        "base-ReAct",
        "Plain single-agent ReAct loop. No routing, no memory, no evolution. "
        "The control level for the orchestration factor.",
        runner_flags={"mode": "react"},
    ),
    Level(
        "self-consistency-N",
        "Sample N independent solutions and majority/judge-select. Accuracy lever "
        "at higher token cost. N configured via runner (default 5).",
        runner_flags={"mode": "react", "self_consistency": "5"},
    ),
    Level(
        "routed",
        "Model routing: cheap model drafts, frontier model escalates on "
        "low-confidence steps. Cost lever — comparable reliability, lower $.",
        runner_flags={"mode": "react", "route": "cheap-to-frontier"},
    ),
    Level(
        "+agenticow-memory",
        "ReAct + agenticow copy-on-write vector memory for agent state across "
        "steps/replicates. Tests whether persistent memory branches the outcome.",
        runner_flags={"mode": "react", "memory": "agenticow"},
    ),
    Level(
        "+darwin-evolved-genome",
        "ReAct driven by a Darwin-evolved harness genome (prompt + tool policy "
        "tuned by the evolution loop). Tests whether evolution moves the needle.",
        runner_flags={"mode": "react", "genome": "darwin-evolved"},
    ),
)

# --------------------------------------------------------------------------
# SCAFFOLD — reasoning scaffold layered on top of the harness.
# --------------------------------------------------------------------------
SCAFFOLD_LEVELS: tuple[Level, ...] = (
    Level("none", "No extra scaffold — the harness runs as-is.",
          runner_flags={"scaffold": "none"}),
    Level("plan-and-solve",
          "Plan-and-Solve: explicit plan step before implementation.",
          runner_flags={"scaffold": "plan-and-solve"}),
    Level("reflexion",
          "Reflexion: self-critique + retry loop on failed verification.",
          runner_flags={"scaffold": "reflexion"}),
)

# --------------------------------------------------------------------------
# LANGUAGE — Retort finds language mostly governs code quality. Configurable;
# the default spans typed/untyped + compiled/interpreted.
# --------------------------------------------------------------------------
LANGUAGE_LEVELS: tuple[Level, ...] = (
    Level("python", "Interpreted, dynamically typed."),
    Level("typescript", "Interpreted, structurally typed."),
    Level("go", "Compiled, statically typed, simple."),
    Level("rust", "Compiled, statically typed, strict."),
)

# --------------------------------------------------------------------------
# TASK — the benchmark task. Levels map to a pinned REQUIREMENTS.json so
# requirement_coverage has a constant denominator (the conformance spec-gate
# is reused untouched). Configurable per workspace.
# --------------------------------------------------------------------------
TASK_LEVELS: tuple[Level, ...] = (
    Level("rest-api-crud", "REST API CRUD service (bundled Retort task)."),
    Level("cli-data-pipeline", "CLI data-processing pipeline (bundled)."),
    Level("brazil-bench", "Brazilian-soccer MCP server (12-requirement spec gate)."),
)


LEVEL_CATALOG: dict[str, tuple[Level, ...]] = {
    F_MODEL: MODEL_LEVELS,
    F_HARNESS: HARNESS_LEVELS,
    F_SCAFFOLD: SCAFFOLD_LEVELS,
    F_LANGUAGE: LANGUAGE_LEVELS,
    F_TASK: TASK_LEVELS,
}

# Default ordering of factors — model first (largest expected effect), then the
# orchestration axis, then scaffold/language/task.
FACTOR_ORDER: tuple[str, ...] = (F_MODEL, F_HARNESS, F_SCAFFOLD, F_LANGUAGE, F_TASK)


def level_doc(factor: str, level_id: str) -> str:
    """Return the documentation string for a (factor, level)."""
    for lvl in LEVEL_CATALOG.get(factor, ()):  # pragma: no branch
        if lvl.id == level_id:
            return lvl.doc
    raise KeyError(f"Unknown level {level_id!r} for factor {factor!r}")


def get_level(factor: str, level_id: str) -> Level:
    """Return the Level object for a (factor, level)."""
    for lvl in LEVEL_CATALOG.get(factor, ()):
        if lvl.id == level_id:
            return lvl
    raise KeyError(f"Unknown level {level_id!r} for factor {factor!r}")


def openrouter_id(model_level: str) -> str:
    """Map a model factor level to its OpenRouter model id."""
    return get_level(F_MODEL, model_level).openrouter


def runner_flags_for(factor: str, level_id: str) -> dict[str, str]:
    """Return the per-cell runner flags contributed by a harness/scaffold level."""
    return dict(get_level(factor, level_id).runner_flags)


def build_registry(
    *,
    models: Sequence[str] | None = None,
    harnesses: Sequence[str] | None = None,
    scaffolds: Sequence[str] | None = None,
    languages: Sequence[str] | None = None,
    tasks: Sequence[str] | None = None,
) -> FactorRegistry:
    """Build a Retort FactorRegistry from selected levels of our factors.

    Pass an explicit subset of level ids per factor to narrow the grid (a
    screening run rarely uses every level of every factor). Any factor left as
    ``None`` defaults to its full documented level set. A factor reduced to a
    single level is *dropped* from the registry (a constant is not a factor) —
    its single value is still applied to every cell by the design layer.

    Returns:
        A FactorRegistry consumable by retort.design.generator / .aliasing.
    """
    selections: dict[str, Sequence[str]] = {
        F_MODEL: models if models is not None else [x.id for x in MODEL_LEVELS],
        F_HARNESS: harnesses if harnesses is not None else [x.id for x in HARNESS_LEVELS],
        F_SCAFFOLD: scaffolds if scaffolds is not None else [x.id for x in SCAFFOLD_LEVELS],
        F_LANGUAGE: languages if languages is not None else [x.id for x in LANGUAGE_LEVELS],
        F_TASK: tasks if tasks is not None else [x.id for x in TASK_LEVELS],
    }

    registry = FactorRegistry()
    for name in FACTOR_ORDER:
        levels = list(selections[name])
        _validate_levels(name, levels)
        if len(levels) < 2:
            # Constant — not a DoE factor. Skipped here; applied per-cell later.
            continue
        ftype = FactorType.ORDINAL if name in ORDINAL_FACTORS else FactorType.CATEGORICAL
        registry.add(name, levels, factor_type=ftype)
    if len(registry) < 2:
        raise ValueError(
            "Need at least 2 varying factors to build a design. "
            f"Got {registry.names}. Widen at least two factors to >1 level."
        )
    return registry


def constant_levels(
    *,
    models: Sequence[str] | None = None,
    harnesses: Sequence[str] | None = None,
    scaffolds: Sequence[str] | None = None,
    languages: Sequence[str] | None = None,
    tasks: Sequence[str] | None = None,
) -> dict[str, str]:
    """Return the {factor: level} for factors pinned to a single level.

    These are factors held constant across the whole design; the design layer
    stamps them onto every cell so the results frame is complete.
    """
    selections: dict[str, Sequence[str] | None] = {
        F_MODEL: models,
        F_HARNESS: harnesses,
        F_SCAFFOLD: scaffolds,
        F_LANGUAGE: languages,
        F_TASK: tasks,
    }
    out: dict[str, str] = {}
    for name, sel in selections.items():
        if sel is not None and len(sel) == 1:
            _validate_levels(name, list(sel))
            out[name] = sel[0]
    return out


def _validate_levels(factor: str, levels: Sequence[str]) -> None:
    known = {lvl.id for lvl in LEVEL_CATALOG[factor]}
    unknown = [x for x in levels if x not in known]
    if unknown:
        raise ValueError(
            f"Unknown level(s) for factor {factor!r}: {unknown}. "
            f"Known: {sorted(known)}"
        )


def describe_factor_model() -> str:
    """Human-readable dump of the full factor model and every level."""
    lines: list[str] = ["Factor model (retort-metaharness)", "=" * 40]
    for name in FACTOR_ORDER:
        lvls = LEVEL_CATALOG[name]
        ordinal = " (ordinal)" if name in ORDINAL_FACTORS else ""
        lines.append(f"\n{name}{ordinal} — {len(lvls)} levels:")
        for lvl in lvls:
            tag = f"  [{lvl.openrouter}]" if lvl.openrouter else ""
            lines.append(f"  - {lvl.id}{tag}: {lvl.doc}")
    return "\n".join(lines) + "\n"
