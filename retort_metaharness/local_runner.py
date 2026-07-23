"""Local backend for metaharness — run a cell on OUR models (Hermes + oMLX).

Path B (2026-07-22, user-directed): evaluate the orchestration factors on local
models with **no OpenRouter and no external solver**. Where ``MetaHarnessRunner``
shells out to the external ``METAHARNESS_SOLVER`` (kept, for the OpenRouter grid),
this ``LocalModelRunner`` **composes Retort's own local pipeline in-process**:

    LocalRunner (provision + Hermes drives the served model)
        → ScoreCollector.collect        (code_quality / test_coverage)
        → cli._spec_conformance_passes   (requirement_coverage, Opus spec-gate)
        → local_inference_cost           (cost_per_task ≈ $0)

Foundation: oMLX returns OpenAI-format ``tool_calls`` for these models, so a local
model drives an agentic tool-loop like a cloud one.

Factor mapping (the generic orchestration; the solver-proprietary
``+agenticow-memory`` / ``+darwin-evolved-genome`` are N/A locally and recorded as
skipped → base-ReAct):

* **base-ReAct**        — one LocalRunner run.
* **self-consistency-N** — N runs; keep the best by test_coverage (a cheap local
  proxy for "did it work") then spec-gate that one.
* **routed**            — draft on the cheap local model (35B); if it fails the
  mechanical gate, escalate to the strong one (80B).
* **scaffold**{none, plan-and-solve, reflexion} — a system-prompt injection.
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path

from retort import cli
from retort.config.schema import EvaluationConfig, LocalAgentConfig
from retort.playpen.local_runner import LocalRunner
from retort.playpen.runner import StackConfig
from retort.playpen.stack_reload import make_stack_manager
from retort.playpen.task_loader import BUNDLED_TASKS_DIR, load_task
from retort.scoring.collector import ScoreCollector
from retort_metaharness import factors as fz
from retort_metaharness.runner import CellResult, CellSpec

logger = logging.getLogger(__name__)

# retort responses used to derive the metaharness CellResult fields.
_METRICS = ["code_quality", "test_coverage"]

_SCAFFOLDS = {
    "none": "",
    "plan-and-solve": (
        " Before writing any code, write a short numbered PLAN of the steps, then "
        "implement each step."
    ),
    "reflexion": (
        " After a first implementation, CRITIQUE your own code against the "
        "requirements and the tests, then revise it before finishing."
    ),
}


class LocalModelRunner:
    """CellRunner that executes a metaharness cell on a local (oMLX) model."""

    name = "local"

    def __init__(
        self,
        *,
        stacks_yaml: str | Path,
        task_source: str = "bundled://rest-api-crud",
        timeout_minutes: int = 45,
        max_turns: int = 200,
        self_consistency_default: int = 5,
        eval_model: str = "opus-4.8",
    ) -> None:
        self.stacks_yaml = Path(stacks_yaml)
        self.task_source = task_source
        self.timeout_minutes = timeout_minutes
        self.max_turns = max_turns
        self.self_consistency_default = self_consistency_default
        self._eval = EvaluationConfig(enabled=True, model=eval_model)
        self._collector = ScoreCollector(metrics=_METRICS)
        self.task = load_task(task_source)
        # requirement checklist for the spec-gate (bundled task dir)
        self._requirements = None
        if task_source.startswith("bundled://"):
            rp = BUNDLED_TASKS_DIR / task_source[len("bundled://"):] / "REQUIREMENTS.json"
            if rp.is_file():
                self._requirements = rp

    def _runner_for(self, served_model: str) -> LocalRunner:
        """A LocalRunner wired to drive `served_model` via Hermes + oMLX."""
        stack_manager = make_stack_manager(self.stacks_yaml)
        return LocalRunner(
            timeout_minutes=self.timeout_minutes,
            max_turns=self.max_turns,
            local_agents={"hermes-local": LocalAgentConfig(harness="hermes", model=served_model)},
            stack_manager=stack_manager,
        )

    def _one_attempt(self, served_model: str, language: str, scaffold: str):
        """Provision + drive one Hermes run; return (output_dir, stack, code_quality,
        test_coverage) or None on a hard failure."""
        runner = self._runner_for(served_model)
        stack = StackConfig(
            language=language,
            agent="hermes-local",
            framework="none",
            extra={"model": served_model, "prompt_injection": _SCAFFOLDS.get(scaffold, "")},
        )
        try:
            env_id = runner.provision(stack, self.task)
            artifacts = runner.execute(env_id, stack, self.task)
        except Exception as exc:  # noqa: BLE001 — a runner crash is a failed cell, not a raise
            logger.warning("local metaharness attempt crashed: %s", exc)
            return None
        if artifacts.output_dir is None:
            return None
        sv = self._collector.collect(artifacts, stack)
        return artifacts.output_dir, stack, sv.get("code_quality") or 0.0, sv.get("test_coverage") or 0.0

    def run(self, spec: CellSpec) -> CellResult:
        served = fz.served_id(spec.model)
        if not served:
            raise ValueError(
                f"LocalModelRunner needs a local model level (served id); got "
                f"{spec.model!r}. Use qwen-80b-local / qwen-35b-local."
            )
        language = spec.levels.get(fz.F_LANGUAGE, "python")
        harness = spec.harness
        scaffold = spec.scaffold if spec.scaffold in _SCAFFOLDS else "none"
        note = ""
        t0 = time.monotonic()

        # --- orchestration by harness_config ---------------------------------
        if harness == "self-consistency-N":
            n = int(spec.runner_flags().get("self_consistency", self.self_consistency_default))
            attempts = [self._one_attempt(served, language, scaffold) for _ in range(n)]
            attempts = [a for a in attempts if a is not None]
            best = max(attempts, key=lambda a: a[3], default=None)  # best test_coverage
            note = f"self-consistency n={n}, kept best of {len(attempts)}"
        elif harness == "routed":
            # cheap draft (35B) → escalate to strong (80B) on a mechanical-gate miss
            draft = fz.served_id("qwen-35b-local") or served
            best = self._one_attempt(draft, language, scaffold)
            if best is None or best[3] <= 0.0:
                strong = fz.served_id("qwen-80b-local") or served
                esc = self._one_attempt(strong, language, scaffold)
                if esc is not None:
                    best = esc
                    note = "routed: escalated 35B→80B"
            else:
                note = "routed: draft (35B) sufficed"
        else:
            if harness in ("+agenticow-memory", "+darwin-evolved-genome"):
                note = f"{harness} N/A on local backend → base-ReAct"
            best = self._one_attempt(served, language, scaffold)

        elapsed = time.monotonic() - t0
        if best is None:
            return CellResult.from_spec(
                spec, status="fail", requirement_coverage=0.0, code_quality=0.0,
                cost_per_task=0.0, latency_s=elapsed, tokens=0, runner=self.name,
                notes=(note + "; no code produced").strip("; "),
            )

        out_dir, _stack, cq, _tcov = best
        # requirement_coverage via retort's spec-gate on the produced code
        req_cov = 0.0
        if self._requirements is not None:
            try:
                shutil.copy2(self._requirements, out_dir / "REQUIREMENTS.json")
            except OSError:
                pass
        try:
            _verdict, rc = cli._spec_conformance_passes(out_dir, self._eval, "public")
            req_cov = rc if rc is not None else 0.0
        except Exception as exc:  # noqa: BLE001 — a flaky judge shouldn't crash the grid
            logger.warning("local metaharness spec-gate failed: %s", exc)

        status = "pass" if req_cov >= 1.0 else "fail"
        return CellResult.from_spec(
            spec, status=status, requirement_coverage=req_cov, code_quality=cq,
            cost_per_task=0.0,  # local ≈ $0; refine with local_inference_cost later
            latency_s=elapsed, tokens=0, runner=self.name, notes=note,
        )
