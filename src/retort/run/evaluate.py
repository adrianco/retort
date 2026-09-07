"""Evaluating a finished run: the judge, the spec gate, and requirements.

Fourth and last cut of the cli.py split. Everything here decides whether a
run passed and produces the artefacts that decision rests on: the LLM judge
(`_run_auto_evaluation`, `_invoke_judge_prompt`, `_invoke_claude_skill`),
the spec-conformance gate (`_spec_conformance_passes` and its helpers
`_build_challenge`, `_declutter_for_eval`, `_shortfalls_claimed`,
`_read_requirement_coverage`), the mechanical gates (`_tests_did_not_run`),
requirements generation (`_ensure_requirements_json`,
`_generate_requirements_from_prompt`), and the eval toolchain preflight.

THE MONKEYPATCH SEAM -- read before adding a test. `_spec_conformance_passes`
calls `_run_auto_evaluation` and `_read_requirement_coverage` by bare name,
so they resolve in THIS module's globals. A test that stubs them must patch
`retort.run.evaluate.<name>`, not `retort.cli.<name>`: `cli` only re-exports
the bindings, and patching a re-export does not reach a caller that lives
here. This is exactly how an earlier suite ended up making billed
`claude -p` calls -- stubs patched a module the code path no longer read.
The autouse `_no_billed_cli_subprocesses` fixture is the backstop; the
guard test beside the conformance tests is the documentation.

Graphify set the boundary: the cluster calls no other cli helper, imports
one thing from persist (`_persist_judge_attempt`, the right direction),
and every external caller is `run_experiments` or a `commands/` module
reaching in via `cli.<name>`. `cli.py` re-exports all sixteen.
`_invoke_claude_skill_prompt` has no caller anywhere and is moved as-is
so this commit stays a pure move; it is a separate deletion.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import click

from retort.run.persist import _persist_judge_attempt

#: Substrings that mean "the judge could not authenticate", as distinct from a
#: judge that ran and returned nothing usable. The credential failure mode here
#: is a BLANKED keychain entry — accessToken and refreshToken both empty strings
#: and expiresAt 0 — which passes every presence check, so the only reliable
#: signal is what the CLI says when it tries to use it.
_AUTH_FAILURE_MARKERS = (
    "failed to authenticate",
    "oauth session expired",
    "not logged in",
    "please run /login",
    "invalid api key",
    "authentication_error",
)


def _is_auth_failure(output: str) -> bool:
    low = (output or "").lower()
    return any(m in low for m in _AUTH_FAILURE_MARKERS)


def _find_skill(skill_name: str, start: Path | None = None) -> Path | None:
    """Locate a skill's SKILL.md by walking upward from ``start`` (or CWD).

    Skills live in ``<repo>/skills/<name>/SKILL.md``. Returns None if not found.
    """
    start = (start or Path.cwd()).resolve()
    candidates = [start, *start.parents]
    # Also try the retort package's repo root (useful when installed from source).
    try:
        import retort as _retort_pkg
        pkg_root = Path(_retort_pkg.__file__).resolve().parent.parent.parent
        candidates.append(pkg_root)
    except Exception:
        pass
    for base in candidates:
        candidate = base / "skills" / skill_name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def _evaluation_is_current(run_dir: Path) -> bool:
    """True if ``evaluation.md`` exists and is newer than every source file."""
    eval_path = run_dir / "evaluation.md"
    if not eval_path.is_file():
        return False
    eval_mtime = eval_path.stat().st_mtime
    ignore_dirs = {"node_modules", "target", "__pycache__", ".git", "summary"}
    ignore_names = {"evaluation.md", "findings.jsonl"}
    for root, dirs, files in os.walk(run_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f in ignore_names:
                continue
            p = Path(root) / f
            try:
                if p.stat().st_mtime > eval_mtime:
                    return False
            except OSError:
                continue
    return True


def _shortfalls_claimed(run_dir: Path) -> list[dict]:
    """The requirements the FIRST opinion claimed were unmet, with its evidence.

    Read from ``assessment.json``'s ``top_findings`` — each carries the requirement
    id, what the evaluator thought was missing, and the evidence it cited.
    """
    p = run_dir / "assessment.json"
    try:
        data = json.loads(p.read_text())
    except (ValueError, OSError):
        return []
    out = []
    for f in data.get("top_findings") or []:
        if not isinstance(f, dict):
            continue
        if f.get("kind") and "requirement" not in str(f.get("kind")):
            continue  # a code-quality finding, not a claimed spec gap
        out.append({
            "id": str(f.get("id") or "?"),
            "title": str(f.get("title") or ""),
            "evidence": str(f.get("evidence") or ""),
        })
    return out


def _tests_did_not_run(scores) -> bool:
    """A run whose tests never executed (``test_coverage == 0``) is not a valid
    success: it offers no proof the code works. Returns True when a
    ``test_coverage`` score is present and zero, so callers can mark the run
    ``failed`` rather than recording a zero-scored "completion". Returns False
    when test_coverage isn't among the responses (no gate to apply).
    """
    for s in getattr(scores, "scores", []):
        if s.metric_name == "test_coverage":
            return s.value == 0.0
    return False


def _read_requirement_coverage(run_dir: Path) -> float | None:
    """Return the eval's requirement_coverage from assessment.json, or None if
    it isn't present/parseable (eval failed or produced no requirement count)."""
    p = run_dir / "assessment.json"
    if not p.exists():
        return None
    try:
        v = json.loads(p.read_text()).get("requirement_coverage")
        return float(v) if v is not None else None
    except (ValueError, TypeError, OSError):
        return None


def _declutter_for_eval(run_dir: Path) -> int:
    """Strip build output from an archived run before the judge reads it.

    The judge is handed the run directory to grade the *source* against a
    requirement checklist — but a scored run also contains whatever the build
    left behind. A Go cell archives a **15.7 MB compiled binary** next to 20 KB of
    source, plus SQLite WAL/SHM files, `__pycache__`, `node_modules`, `target/`.
    The judge then explores 16 MB to grade 20 KB.

    Removing it is safe (the scorer has already built and tested; these are
    outputs, not inputs) and pays twice: the eval is faster, and the judge has
    less irrelevant material to misread — this judge disagrees with itself on
    identical code (mean 0.18, max 0.92 requirement-coverage swing), and clutter
    is one plausible contributor.

    Returns the number of entries removed.
    """
    removed = 0
    _DIRS = {"__pycache__", "node_modules", "target", ".pytest_cache", ".venv",
             "build", "dist", ".gradle", ".mypy_cache", ".ruff_cache"}
    _SUFFIXES = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".pyc",
                 ".class", ".o", ".so", ".dylib", ".beam")
    for p in sorted(run_dir.rglob("*"), key=lambda x: -len(x.parts)):
        try:
            if p.is_dir():
                if p.name in _DIRS:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
                continue
            if p.name.endswith(_SUFFIXES):
                p.unlink()
                removed += 1
                continue
            # A compiled executable: no suffix, executable bit, and big. Source
            # files and scripts never look like this.
            if (
                "." not in p.name
                and p.stat().st_size > 512_000
                and os.access(p, os.X_OK)
            ):
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _build_challenge(shortfalls: list[dict], coverage: float | None) -> str:
    """An 'are you sure?' prompt for the SECOND opinion.

    The second opinion exists to catch **false failures** — a complete implementation
    that the first evaluator marked short because it didn't find the code. A blind
    re-roll is a poor way to do that: it just draws another sample from a noisy judge
    (measured: mean requirement_coverage swing 0.18 between two reads of *identical*
    code, max 0.92). Re-checking the *specific* claims is both more reliable and
    cheaper — the evaluator re-examines a handful of requirements instead of
    re-grading the whole spec.

    The prompt deliberately asks it to go **looking for the implementation**, because
    that is the failure mode being guarded against. It must still be able to confirm a
    genuine gap — the gate fails on two short opinions — so it is asked for
    file:line evidence either way, not for a verdict it can hand back on vibes.
    """
    claims = "\n".join(
        f"  - {s['id']}: {s['title']}\n      first evaluator's evidence: {s['evidence']}"
        for s in shortfalls
    ) or "  (the first pass recorded no specific requirement findings)"
    return (
        "\n\nSECOND OPINION — you are RE-CHECKING a prior evaluation, not starting fresh.\n"
        f"A first evaluation scored requirement_coverage={coverage} and claimed these "
        "requirements were NOT met:\n"
        f"{claims}\n\n"
        "For EACH claim above: are you sure? Go and look for the implementation in the "
        "code before accepting that it is missing.\n"
        "  - If you FIND it, the first evaluator was wrong — say so and cite file:line.\n"
        "  - If it is genuinely absent or incomplete, confirm it and cite what you "
        "checked.\n"
        "First evaluations miss existing implementations more often than they invent "
        "them, so the burden of proof is on the claim that something is MISSING.\n"
        "Then re-score requirement_coverage over the FULL checklist and write "
        "assessment.json as usual."
    )


def _eval_tooling_preflight(eval_model: str, runs_root: Path) -> tuple[bool, str]:
    """Confirm the second-opinion eval tooling is actually usable before a batch.

    Checks (a) the evaluate-run skill is discoverable and (b) the judge model
    answers a trivial prompt. Returns (ok, message). Catches the silent-failure
    class where reevaluate "succeeds" but the judge never ran (CLI missing,
    model unreachable, usage exhausted) — persisting nothing while reporting
    success.
    """
    import subprocess

    from retort.playpen.local_runner import _find_skill_path, _model_cli_args
    shown = eval_model or "latest (CLI default)"
    start = next((r for c in runs_root.iterdir() if c.is_dir()
                  for r in c.iterdir() if r.is_dir()), runs_root)
    if _find_skill_path("evaluate-run", start=start) is None:
        return False, "evaluate-run skill not found (cannot grade requirement_coverage)"
    try:
        proc = subprocess.run(
            ["claude", "-p", "Reply with exactly: OK", *_model_cli_args(eval_model),
             "--output-format", "text", "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=90,
        )
    except FileNotFoundError:
        return False, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"judge model {shown} did not respond within 90s"
    if proc.returncode != 0:
        return False, (f"judge model {shown} probe failed "
                       f"(exit {proc.returncode}): {proc.stderr.strip()[:140]}")
    if "OK" not in (proc.stdout or ""):
        return False, f"judge model {shown} returned no usable output"
    return True, f"judge {shown} reachable, evaluate-run skill present"


def _generate_requirements_from_prompt(task) -> dict:
    """Derive a requirement checklist from a task's prompt as a fallback.

    Extracts bullet lines ("- …") from the prompt so requirement_coverage has
    a stable, non-zero denominator even when the task ships no pinned checklist.
    This is a best-effort stand-in for a hand-authored REQUIREMENTS.json — the
    caller warns that it should be reviewed and committed.
    """
    bullets: list[str] = []
    for raw in (getattr(task, "prompt", "") or "").splitlines():
        line = raw.strip()
        if line[:1] in {"-", "*"} and len(line) > 2:
            text = line[1:].strip()
            if text and text.lower() not in {b.lower() for b in bullets}:
                bullets.append(text)
    if not bullets:
        # No bullets — fall back to the one-line description as a single item.
        desc = (getattr(task, "description", "") or "").strip().splitlines()
        bullets = [desc[0]] if desc else ["Implements the task as described."]
    return {
        "task": getattr(task, "name", "unknown"),
        "note": (
            "AUTO-GENERATED from the task prompt because the task shipped no "
            "REQUIREMENTS.json. Review and pin this checklist for a stable, "
            "comparable requirement_coverage denominator."
        ),
        "generated": True,
        "requirements": [
            {"id": f"R{i}", "requirement": b, "how_to_verify": "Derived from the task prompt."}
            for i, b in enumerate(bullets, 1)
        ],
    }


def _ensure_requirements_json(config_dir, task, task_source, requirements_path_fn) -> None:
    """Guarantee ``<experiment>/REQUIREMENTS.json`` exists before runs grade.

    Order: respect an existing file (pinned), else copy the task's canonical
    checklist, else generate one from the prompt and warn. Never raises.
    """
    import shutil

    dest = config_dir / "REQUIREMENTS.json"
    if dest.exists():
        return
    try:
        bundled = requirements_path_fn(task_source)
    except Exception:
        bundled = None
    if bundled is not None:
        try:
            shutil.copyfile(bundled, dest)
            click.echo(f"  Requirements: copied pinned checklist from {task.name} task.")
            return
        except OSError:
            pass
    # Last resort: derive from the prompt so the denominator is at least stable.
    try:
        data = _generate_requirements_from_prompt(task)
        dest.write_text(json.dumps(data, indent=2))
        click.echo(
            f"  ⚠ Requirements: no pinned REQUIREMENTS.json for task {task.name!r} — "
            f"generated {len(data['requirements'])} from the prompt. Review "
            f"{dest} and commit it for comparable scoring.",
            err=True,
        )
    except Exception as exc:
        click.echo(f"  (could not write REQUIREMENTS.json: {exc})", err=True)


def _invoke_claude_skill_prompt(
    prompt: str,
    model: str,
    timeout: int = 600,
) -> tuple[int, str]:
    """Invoke claude with a pre-built prompt. Returns (exit_code, combined_output).

    Timeout defaults to 600s to accommodate chained skills (evaluate-run +
    file-run-issues) in a single call.
    """
    from retort.playpen.local_runner import _model_cli_args
    cmd = [
        "claude", "-p", prompt,
        *_model_cli_args(model),
        "--output-format", "text",
        "--dangerously-skip-permissions",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"skill invocation timed out after {timeout}s"
    except Exception as exc:
        return 1, f"skill invocation failed: {exc}"


def _invoke_claude_skill(
    skill_path: Path,
    params: dict[str, str],
    model: str,
    timeout: int = 300,
) -> tuple[int, str]:
    """Invoke a claude skill via ``claude -p``. Returns (exit_code, combined_output).

    Never raises — a missing ``claude`` binary or a non-zero exit is reported
    through the returned code and stderr text so callers can log and continue.
    """
    from retort.playpen.local_runner import _model_cli_args
    param_str = " ".join(f"{k}={v}" for k, v in params.items())
    prompt = f"Follow skill at {skill_path} for {param_str}"
    cmd = [
        "claude", "-p", prompt,
        *_model_cli_args(model),
        "--output-format", "text",
        "--dangerously-skip-permissions",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"skill invocation timed out after {timeout}s"
    except Exception as exc:
        return 1, f"skill invocation failed: {exc}"


def _invoke_judge_prompt(judge, run_dir: Path, prompt: str) -> tuple[int, str]:
    """Run a selected evaluation judge against one archived workspace."""
    from retort.evaluation.judges import judge_runner

    cmd = judge_runner(judge).build_command(judge, run_dir, prompt)
    started = time.monotonic()
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.run(
            cmd,
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=judge.timeout_seconds,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode
    except FileNotFoundError:
        exit_code = 127
        stderr = f"judge CLI {judge.harness!r} not found on PATH"
    except subprocess.TimeoutExpired:
        exit_code = 124
        stderr = f"judge timed out after {judge.timeout_seconds}s"
    except Exception as exc:
        exit_code = 1
        stderr = f"judge invocation failed: {exc}"
    _persist_judge_attempt(
        run_dir,
        judge,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.monotonic() - started,
    )
    return exit_code, stdout + stderr


def _run_auto_evaluation(
    run_dir: Path,
    eval_config,
    visibility: str,
    *,
    force: bool = False,
    extra_prompt: str = "",
    local_agents=None,
) -> None:
    """Invoke evaluate-run + file-run-issues through the selected judge.

    Both skills are chained into one prompt so the subprocess starts once,
    reads context once, and writes all outputs in a single session. Never
    raises. Skips when evaluation.md is already current unless force is set.
    Private experiments are clamped to the beads tracker.
    """
    if not eval_config.enabled:
        return
    from retort.evaluation.judges import JudgeConfigurationError, resolve_judge
    try:
        judge = resolve_judge(eval_config, local_agents or {})
    except JudgeConfigurationError as exc:
        click.echo(f"  (evaluate: invalid judge: {exc})", err=True)
        return
    if not run_dir.is_dir():
        click.echo(f"  (evaluate: {run_dir} missing, skipping)", err=True)
        return
    if not force and _evaluation_is_current(run_dir):
        click.echo(f"  (evaluate: {run_dir.name} up-to-date, skipping)")
        return

    eval_skill = _find_skill("evaluate-run", start=run_dir)
    if eval_skill is None:
        click.echo("  (evaluate: skills/evaluate-run not found, skipping)", err=True)
        return

    # Private experiments never reach GitHub.
    tracker = eval_config.issue_tracker
    if visibility == "private" and tracker != "beads":
        tracker = "beads"

    file_skill = _find_skill("file-run-issues", start=run_dir)

    click.echo(
        f"  evaluating {run_dir.name} "
        f"(judge={judge.harness}, model={judge.model})..."
    )

    if file_skill is not None:
        # Chain both skills into one subprocess: one cold-start, one context load.
        prompt = (
            f"Follow skill at {eval_skill} for run_dir={run_dir}. "
            f"Then follow skill at {file_skill} for "
            f"run_dir={run_dir} tracker={tracker} "
            f"min_severity={eval_config.min_severity_to_file}."
        ) + (extra_prompt or "")
        rc, output = _invoke_judge_prompt(judge, run_dir, prompt)
    elif extra_prompt:
        rc, output = _invoke_judge_prompt(
            judge,
            run_dir,
            f"Follow skill at {eval_skill} for run_dir={run_dir}.{extra_prompt}",
        )
    else:
        rc, output = _invoke_judge_prompt(
            judge, run_dir, f"Follow skill at {eval_skill} for run_dir={run_dir}"
        )

    if rc != 0:
        # An AUTH failure is different in kind from a judge that ran and could
        # not decide. It will fail identically for every remaining cell, and
        # "continuing" then records a whole experiment with requirement_coverage
        # NULL — data that looks complete and silently cannot be pooled with any
        # other run. Stop instead, so --resume can finish it after a /login.
        if _is_auth_failure(output):
            raise click.ClickException(
                "JUDGE NOT AUTHENTICATED — stopping rather than recording "
                "ungated runs.\n\n"
                f"    {output.strip()[:200]}\n\n"
                "  Every remaining cell would fail the same way and be recorded "
                "with requirement_coverage NULL, which looks like complete data "
                "and cannot be pooled with any other experiment.\n"
                "  Fix: run `/login` at an interactive terminal (it is local-only "
                "and does not work over Remote Control), then re-run with "
                "--resume to finish the remaining cells.\n"
                "  Check first with: claude -p 'Reply with exactly: OK'"
            )
        click.echo(f"  (evaluate failed rc={rc}; continuing) {output[:200]}", err=True)


def _spec_conformance_passes(
    run_dir, eval_config, visibility, *, local_agents=None
) -> tuple[bool | None, float | None]:
    """Second-opinion spec gate. Returns ``(verdict, coverage)``:

    * ``True``  — a real eval found requirement_coverage == 1.0 (pass).
    * ``False`` — two real evals both fell short (genuine spec gap).
    * ``None``  — inconclusive: the eval could not run (usage limit / timeout),
      so there aren't two real opinions. The caller should retry later rather
      than record a failure — this keeps an infra hiccup from masquerading as a
      spec failure.

    A run fails only on two short opinions, so borderline judge noise on a single
    requirement can't sink a complete run while a real omission still does.

    **The second opinion is a CHALLENGE, not an independent re-roll.** It used to be
    the latter: the first eval's output was deleted and the judge graded the whole
    spec again from scratch. That is a weak way to catch a false failure, because it
    just draws another sample from a noisy judge — measured across 22 paired reads of
    *identical* code, requirement_coverage moved by a mean of 0.18 and as much as
    0.92. The second pass now receives the specific requirements the first pass
    claimed were missing, plus its evidence, and is asked to go and look for the
    implementation ("are you sure?"). Focused, so it is also cheaper.

    The trade is deliberate: independence is exchanged for a targeted verification.
    Anchoring is the risk, so the prompt puts the burden of proof on the claim that
    something is MISSING (the failure mode being guarded against) and demands
    file:line evidence either way — it can still confirm a genuine gap, which is what
    keeps a real omission failing.
    """
    reals: list[float] = []
    challenge = ""
    for attempt in (1, 2):
        # Before wiping the first opinion's output, capture WHAT it claimed was
        # missing — the second opinion re-checks those specific claims rather than
        # blindly re-rolling a noisy judge. See _build_challenge.
        if attempt == 2:
            challenge = _build_challenge(
                _shortfalls_claimed(run_dir), reals[-1] if reals else None
            )
        # Clear prior eval output, so a failed/partial eval leaves no file
        # and _read_requirement_coverage returns None (inconclusive) — never a
        # stale value from an earlier eval misread as this run's fresh result.
        for fname in ("assessment.json", "evaluation.md", "findings.jsonl"):
            try:
                (run_dir / fname).unlink()
            except (FileNotFoundError, IsADirectoryError, TypeError):
                pass
        if attempt == 1:
            # Give the judge the source, not the build output (see
            # _declutter_for_eval). Done once, before the first opinion — both
            # attempts then grade byte-identical material, which is the whole
            # point of a second opinion.
            _declutter_for_eval(run_dir)
        _run_auto_evaluation(
            run_dir,
            eval_config,
            visibility,
            force=True,
            extra_prompt=challenge,
            local_agents=local_agents,
        )
        cov = _read_requirement_coverage(run_dir)
        if cov is None:
            click.echo(f"    spec gate attempt {attempt}/2: eval did not run (inconclusive)")
            continue
        reals.append(cov)
        if cov >= 1.0:
            if attempt == 2:
                click.echo("    spec gate: passed on second opinion")
            return True, cov
        click.echo(
            f"    spec gate attempt {attempt}/2: requirement_coverage={cov} (<1.0)"
        )
    if len(reals) >= 2:
        return False, max(reals)   # two real opinions, both short -> genuine fail
    if len(reals) == 1:
        return None, reals[0]      # only one real opinion (other couldn't run)
    return None, None              # no real opinions at all
