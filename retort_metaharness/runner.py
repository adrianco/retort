"""Runner glue — invoke the per-cell metaharness runner, one cell at a time.

This is the *glue*, not the runner. The per-cell ``playpen`` runner (built
separately) is responsible for: provisioning an isolated workspace, driving the
metaharness agent (model routing / agenticow memory / darwin genome toggled per
the cell's factor levels), and producing code. Retort then scores that code with
its existing scorers + the conformance spec-gate (pinned REQUIREMENTS.json +
judge), which we reuse untouched for fairness.

Two runners are provided:

- ``MetaHarnessRunner``  — shells out to the real per-cell runner via a
  configurable command (``$METAHARNESS_RUNNER_CMD`` or constructor arg). Maps
  factor levels → runner flags and parses a JSON result. The contract is
  documented in ``MetaHarnessRunner.run``. Use this for the real paid grid.

- ``LocalStubRunner``    — a $0, no-LLM deterministic fixture used only to prove
  the pipeline end-to-end (design→run→score→ANOVA→diagnose→report). It writes
  real source files to an isolated workspace and measures real properties of
  them; its metric values are a documented deterministic function of the cell
  (no model is ever called). NOT a model benchmark.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from retort_metaharness import (
    RESP_CODE_QUALITY,
    RESP_COST_PER_TASK,
    RESP_LATENCY,
    RESP_REQUIREMENT_COVERAGE,
)
from retort_metaharness import factors as fz
from retort_metaharness import openrouter as orouter

# Coverage at/above this fraction = the cell satisfied the spec gate (pass).
PASS_THRESHOLD = 0.70


@dataclass(frozen=True)
class CellSpec:
    """A single cell to execute: its factor levels + replicate index."""

    cell_id: str
    levels: dict[str, str]
    replicate: int = 0

    @property
    def model(self) -> str:
        return self.levels.get(fz.F_MODEL, "unknown")

    @property
    def harness(self) -> str:
        return self.levels.get(fz.F_HARNESS, "base-ReAct")

    @property
    def scaffold(self) -> str:
        return self.levels.get(fz.F_SCAFFOLD, "none")

    @property
    def language(self) -> str:
        return self.levels.get(fz.F_LANGUAGE, "python")

    @property
    def task(self) -> str:
        return self.levels.get(fz.F_TASK, "rest-api-crud")

    def runner_flags(self) -> dict[str, str]:
        """Per-cell flags the metaharness runner is invoked with.

        Combines the harness-config and scaffold runner_flags plus the model's
        OpenRouter id. This is exactly the model-routing / agenticow-memory /
        darwin-genome toggling driven by the factor levels.
        """
        flags: dict[str, str] = {}
        flags["model"] = fz.openrouter_id(self.model) or self.model
        flags.update(fz.runner_flags_for(fz.F_HARNESS, self.harness))
        flags.update(fz.runner_flags_for(fz.F_SCAFFOLD, self.scaffold))
        flags["language"] = self.language
        flags["task"] = self.task
        return flags


@dataclass
class CellResult:
    """Result of executing one cell. Flat — one row of the results frame."""

    cell_id: str
    replicate: int
    # factor levels (flattened for the results CSV)
    model: str
    harness_config: str
    scaffold: str
    language: str
    task: str
    # outcome
    status: str  # "pass" | "fail"
    # responses
    requirement_coverage: float
    code_quality: float
    cost_per_task: float
    latency_s: float
    # raw meter
    tokens: int
    runner: str
    notes: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_row(self) -> dict[str, object]:
        d = asdict(self)
        extra = d.pop("extra")
        d.update({f"x_{k}": v for k, v in extra.items()})
        return d

    @classmethod
    def from_spec(
        cls,
        spec: CellSpec,
        *,
        status: str,
        requirement_coverage: float,
        code_quality: float,
        cost_per_task: float,
        latency_s: float,
        tokens: int,
        runner: str,
        notes: str = "",
        extra: dict[str, str] | None = None,
    ) -> CellResult:
        return cls(
            cell_id=spec.cell_id,
            replicate=spec.replicate,
            model=spec.model,
            harness_config=spec.harness,
            scaffold=spec.scaffold,
            language=spec.language,
            task=spec.task,
            status=status,
            requirement_coverage=requirement_coverage,
            code_quality=code_quality,
            cost_per_task=cost_per_task,
            latency_s=latency_s,
            tokens=tokens,
            runner=runner,
            notes=notes,
            extra=extra or {},
        )


@runtime_checkable
class CellRunner(Protocol):
    """Protocol for anything that can execute one cell and return a result."""

    name: str

    def run(self, spec: CellSpec) -> CellResult: ...


# --------------------------------------------------------------------------
# Real runner adapter — shells out to the per-cell metaharness `playpen` runner
# --------------------------------------------------------------------------
class MetaHarnessRunner:
    """Adapter that invokes the per-cell metaharness runner.

    Contract with the runner (the ``playpen`` runner built separately):

      The command is invoked as::

          <cmd> --cell-json <path-to-cell.json> --out <path-to-result.json>

      where cell.json contains::

          {"cell_id": ..., "replicate": ..., "levels": {...},
           "flags": {"model": "<openrouter-id>", "mode": "react",
                     "route": "...", "memory": "agenticow",
                     "genome": "darwin-evolved", "self_consistency": "5",
                     "scaffold": "reflexion", "language": "...", "task": "..."}}

      and the runner must, after provisioning an isolated workspace, driving the
      metaharness agent, and letting Retort score the result via the conformance
      spec-gate, write result.json::

          {"status": "pass"|"fail",
           "requirement_coverage": float,   # from the pinned REQUIREMENTS.json
           "code_quality": float,           # Retort code-quality scorer
           "cost_per_task": float,          # metered USD
           "latency_s": float,              # wall-clock
           "tokens": int,
           "notes": "..."}

    The command template can also be set with ``$METAHARNESS_RUNNER_CMD``. This
    keeps the two layers decoupled: we own design/analysis/diagnosis/reporting,
    the runner owns provisioning/agent-execution/scoring.
    """

    name = "metaharness"

    def __init__(self, cmd: str | None = None, timeout: float = 3600.0) -> None:
        self.cmd = cmd or os.environ.get("METAHARNESS_RUNNER_CMD", "")
        self.timeout = timeout
        if not self.cmd:
            raise RuntimeError(
                "No metaharness runner command. Set --runner-cmd or "
                "$METAHARNESS_RUNNER_CMD to the per-cell runner entrypoint "
                "(the playpen runner). For a $0 dry run use the local-stub runner."
            )

    def run(self, spec: CellSpec) -> CellResult:
        with tempfile.TemporaryDirectory(prefix=f"mh-{spec.cell_id}-") as td:
            cell_path = Path(td) / "cell.json"
            out_path = Path(td) / "result.json"
            cell_path.write_text(
                json.dumps(
                    {
                        "cell_id": spec.cell_id,
                        "replicate": spec.replicate,
                        "levels": spec.levels,
                        "flags": spec.runner_flags(),
                    }
                ),
                encoding="utf-8",
            )
            argv = shlex.split(self.cmd) + [
                "--cell-json", str(cell_path),
                "--out", str(out_path),
            ]
            t0 = time.perf_counter()
            proc = subprocess.run(  # noqa: S603
                argv, capture_output=True, text=True, timeout=self.timeout
            )
            wall = time.perf_counter() - t0

            if not out_path.exists():
                # The runner produced no result file — treat as a $0/instant
                # tooling failure so diagnose.py flags it (harness bug, not model).
                return CellResult.from_spec(
                    spec,
                    status="fail",
                    requirement_coverage=0.0,
                    code_quality=0.0,
                    cost_per_task=0.0,
                    latency_s=round(wall, 4),
                    tokens=0,
                    runner=self.name,
                    notes=(
                        f"runner produced no result.json (exit={proc.returncode}); "
                        f"stderr={proc.stderr[-300:]!r}"
                    ),
                )
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return CellResult.from_spec(
                spec,
                status=str(data.get("status", "fail")),
                requirement_coverage=float(data.get(RESP_REQUIREMENT_COVERAGE, 0.0)),
                code_quality=float(data.get(RESP_CODE_QUALITY, 0.0)),
                cost_per_task=float(data.get(RESP_COST_PER_TASK, 0.0)),
                latency_s=float(data.get(RESP_LATENCY, wall)),
                tokens=int(data.get("tokens", 0)),
                runner=self.name,
                notes=str(data.get("notes", "")),
            )


# --------------------------------------------------------------------------
# $0 local stub — exercises the pipeline without any LLM call
# --------------------------------------------------------------------------
class LocalStubRunner:
    """A $0, no-LLM deterministic runner for pipeline smoke tests.

    It genuinely writes source files to an isolated workspace and measures real
    properties (file length → token count → cost via the published price table;
    real wall-clock latency). Its quality/coverage values are a *documented
    deterministic function of the cell* — there is no model, so this is NOT a
    model benchmark. It exists purely to prove design→run→score→ANOVA→diagnose
    →report works end-to-end before the real (paid) runner is wired in.

    It also reproduces two real-world failure modes so the diagnosis layer has
    something to classify:

      * unsupported language  → the harness emits nothing ($0 / instant fail)
        = TOOLING_FALSE_FAIL.
      * a known-buggy combo (self-consistency-N + reflexion) → the runner
        "crashes" composing the two ($0 / instant fail) = TOOLING_FALSE_FAIL.

    Everything else runs to completion; cells below PASS_THRESHOLD coverage are
    genuine model-fails (cost > 0, time > 0) = GENUINE_MODEL_FAIL.
    """

    name = "local-stub"
    SUPPORTED_LANGS = ("python", "typescript", "go")

    # Documented per-level deterministic contributions (fixture, not measured).
    _MODEL_COVERAGE = {
        "deepseek-v4-pro": 0.62, "glm-5.2": 0.66,
        "opus-4.8": 0.78, "gpt-5.2": 0.75, "unknown": 0.60,
    }
    _MODEL_QUALITY = {
        "deepseek-v4-pro": 0.60, "glm-5.2": 0.63,
        "opus-4.8": 0.80, "gpt-5.2": 0.77, "unknown": 0.58,
    }
    _HARNESS_COV_BONUS = {
        "base-ReAct": 0.00, "self-consistency-N": 0.08, "routed": 0.01,
        "+agenticow-memory": 0.05, "+darwin-evolved-genome": 0.07,
    }
    _HARNESS_COST_MULT = {
        "base-ReAct": 1.0, "self-consistency-N": 5.0, "routed": 0.45,
        "+agenticow-memory": 1.1, "+darwin-evolved-genome": 1.2,
    }
    _SCAFFOLD_COV_BONUS = {"none": 0.0, "plan-and-solve": 0.03, "reflexion": 0.06}
    _LANG_QUALITY = {"python": 0.0, "typescript": 0.05, "go": 0.08, "rust": 0.10}

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(
            workspace_root or tempfile.mkdtemp(prefix="mh-stub-")
        )
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _emit_artifact(self, spec: CellSpec, ws: Path) -> str:
        """Write a tiny but real source artifact for the cell. Returns its text."""
        lang = spec.language
        ext = {"python": "py", "typescript": "ts", "go": "go"}.get(lang, "txt")
        # The artifact length scales with harness/scaffold so token counts (and
        # therefore measured cost) genuinely differ across cells.
        n_funcs = 6 + len(spec.harness) % 4 + (2 if spec.scaffold == "reflexion" else 0)
        body_lines = [f"# task={spec.task} model={spec.model} harness={spec.harness}"]
        for i in range(n_funcs):
            if lang == "python":
                body_lines += [f"def handler_{i}(req):", f"    return process_{i}(req)"]
            elif lang == "typescript":
                body_lines += [f"export function handler{i}(req: Req): Resp {{",
                               f"  return process{i}(req);", "}"]
            else:  # go
                body_lines += [f"func Handler{i}(r *Req) *Resp {{",
                               f"  return process{i}(r)", "}"]
        body_lines += ["# tests", "def test_handlers(): assert True"]
        text = "\n".join(body_lines) + "\n"
        (ws / f"service.{ext}").write_text(text, encoding="utf-8")
        (ws / f"test_service.{ext}").write_text("assert True\n", encoding="utf-8")
        return text

    def run(self, spec: CellSpec) -> CellResult:
        t0 = time.perf_counter()
        ws = self.workspace_root / f"{spec.cell_id}-r{spec.replicate}"
        ws.mkdir(parents=True, exist_ok=True)

        # --- Failure mode 1: unsupported language → harness emits nothing.
        if spec.language not in self.SUPPORTED_LANGS:
            return CellResult.from_spec(
                spec, status="fail", requirement_coverage=0.0, code_quality=0.0,
                cost_per_task=0.0, latency_s=round(time.perf_counter() - t0, 5),
                tokens=0, runner=self.name,
                notes=f"unsupported language {spec.language!r}: harness produced no output",
            )

        # --- Failure mode 2: unimplemented harness path → runner crash, no
        # output. The stub never wired the self-consistency-N sampler, so every
        # such cell is a $0/instant tooling fail (this is exactly the class the
        # diagnosis layer must separate from real model failures).
        if spec.harness == "self-consistency-N":
            return CellResult.from_spec(
                spec, status="fail", requirement_coverage=0.0, code_quality=0.0,
                cost_per_task=0.0, latency_s=round(time.perf_counter() - t0, 5),
                tokens=0, runner=self.name,
                notes="self-consistency-N sampler not implemented in local-stub (runner crash)",
            )

        # --- Normal path: emit a real artifact and measure it.
        text = self._emit_artifact(spec, ws)

        # Real measured token count (chars/4), scaled by harness sampling.
        base_tokens = max(1, len(text) // 4)
        mult = self._HARNESS_COST_MULT.get(spec.harness, 1.0)
        tokens = int(base_tokens * mult * 12)  # ×12 ≈ prompt+context realism
        usage = orouter.Usage(prompt_tokens=tokens * 3 // 4, completion_tokens=tokens // 4)
        cost = orouter.cost_usd(fz.openrouter_id(spec.model) or "", usage)

        # Deterministic coverage/quality from the documented fixture.
        cov = (
            self._MODEL_COVERAGE.get(spec.model, 0.60)
            + self._HARNESS_COV_BONUS.get(spec.harness, 0.0)
            + self._SCAFFOLD_COV_BONUS.get(spec.scaffold, 0.0)
        )
        cov = max(0.0, min(1.0, cov))
        qual = (
            self._MODEL_QUALITY.get(spec.model, 0.58)
            + self._LANG_QUALITY.get(spec.language, 0.0)
        )
        qual = max(0.0, min(1.0, qual))

        # A small real busy-loop so wall-clock latency is nonzero and jittery —
        # this is the one response with genuine run-to-run residual variance.
        acc = 0.0
        for i in range(20000):
            acc += (i % 7) * 0.5
        latency = time.perf_counter() - t0

        status = "pass" if cov >= PASS_THRESHOLD else "fail"
        return CellResult.from_spec(
            spec, status=status, requirement_coverage=round(cov, 4),
            code_quality=round(qual, 4), cost_per_task=round(cost, 6),
            latency_s=round(latency, 5), tokens=tokens, runner=self.name,
            notes="local-stub fixture (no LLM)",
            extra={"workspace": str(ws), "_acc": f"{acc:.1f}"},
        )


def run_plan(runner: CellRunner, cells: list[CellSpec]) -> list[CellResult]:
    """Execute every cell spec with the given runner (sequentially)."""
    return [runner.run(spec) for spec in cells]


def expand_cells(plan_configs: list[dict[str, str]], replicates: int) -> list[CellSpec]:
    """Expand a list of {factor: level} cell configs into replicated CellSpecs."""
    specs: list[CellSpec] = []
    for cfg in plan_configs:
        cell_id = str(cfg.get("cell_id", f"c{len(specs):03d}"))
        levels = {k: v for k, v in cfg.items() if k != "cell_id"}
        for r in range(replicates):
            specs.append(CellSpec(cell_id=cell_id, levels=levels, replicate=r))
    return specs
