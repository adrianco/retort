"""The run workspace on disk: seeding a repair, archiving a result, gitignore.

Third cut of the cli.py split. Everything here manipulates the playpen
workspace as files -- copying a prior attempt in so self-repair has
something to fix (`_seed_repair_workspace`, `_repair_prior_run`), archiving a
finished run into experiments/ with the build noise stripped
(`_archive_run_workspace`, `_ignore_archive_noise`, `_ARCHIVE_NOISE`), the
.gitignore a new experiment directory gets (`_gitignore_for` and the three
`_GITIGNORE_*` templates), and turning an agent's failure into a
classification (`_harness_failure`). None of it touches the database.

Graphify set the boundary: three of these serve only `run_experiments`, one
is called only by the other two, and the remaining two are reached by
`commands/` via `cli.<name>`. `cli.py` re-exports the six functions. The
constants are NOT re-exported -- their only code users are in this file
(external mentions of `_ARCHIVE_NOISE` are comments, updated to point here).
"""
from __future__ import annotations

import json
from pathlib import Path

import click

_GITIGNORE_COMMON = """\
# Retort — workspace-local state
retort.db
retort.db-journal
retort.db-shm
retort.db-wal

# Build output / vendored deps must never be committed, even inside runs/.
# (The archiver strips these too; this is defense-in-depth for public
# experiments where runs/ is tracked — node_modules in particular embeds
# third-party files that trip secret scanners.)
**/node_modules/
**/_build/
**/deps/
**/target/
**/__pycache__/
**/.cpcache/
**/.rebar3/
**/.elixir_ls/
**/erl_crash.dump
"""


_GITIGNORE_PRIVATE_EXTRA = """\

# Retort — visibility=private: keep all generated artifacts local
runs/
reports/
evaluation.md
findings.jsonl
TASK.md
"""


_GITIGNORE_PUBLIC_EXTRA = """\

# Retort — visibility=public: artifacts (runs/, reports/web/) are tracked
# Only ignore caches and intermediate scratch.
.retort-cache/
"""


# Build output / vendored dependency directories (and crash dumps) that must
# never enter a run archive — regenerable, large, and a source of committed
# secrets (node_modules fixtures) and copy failures (dangling _build symlinks).
_ARCHIVE_NOISE = {
    "node_modules", "_build", "deps", "target", "build", "dist", "vendor",
    "__pycache__", ".gradle", ".cpcache", ".rebar3", ".elixir_ls",
    ".pytest_cache", ".mypy_cache", ".git",
    # Python venvs — retort now provisions one into every python workspace
    # (see playpen.local_runner.ensure_python_venv), so without this every
    # python run would copy ~17 MB of thousands of small files into the archive.
    # It is pure waste twice over: `venv/` is gitignored so it is never
    # committed, AND a copied venv is BROKEN — its scripts hard-code the
    # original playpen path, which no longer exists. Leaving it out is also what
    # makes rescoring correct: `find_venv` then misses, and the scorer builds a
    # fresh working venv instead of activating a dead one.
    "venv", ".venv",
    # Hook debris. Editor/agent plugins active on this machine write their own
    # state INTO the playpen — `.swarm/`, `.claude-flow/` and a 1.5 MB
    # `ruvector.db` per run. None of it is the model's work, retort does not use
    # any of it, and copying it makes the archive both larger and less honest:
    # a scorer walking the tree sees files no agent wrote.
    ".swarm", ".claude-flow", "ruvector.db", ".hive-mind",
    # Swift's build dir. Not merely large: its ModuleCache bakes ABSOLUTE paths
    # into precompiled modules, so a copied .build actively breaks the next
    # build — "missing required module 'SwiftShims'" — the same way a copied
    # venv breaks. Leading dot, so it slipped past both the name list and the
    # startswith("_") rule in _seed_repair_workspace.
    ".build",
}


def _ignore_archive_noise(_dir: str, names: list[str]) -> set[str]:
    """`shutil.copytree` ignore callback: skip build output and vendored deps."""
    return {n for n in names if n in _ARCHIVE_NOISE or n == "erl_crash.dump"}


def _gitignore_for(visibility: str) -> str:
    """Return the .gitignore body for a given visibility level."""
    extra = _GITIGNORE_PUBLIC_EXTRA if visibility == "public" else _GITIGNORE_PRIVATE_EXTRA
    return _GITIGNORE_COMMON + extra


def _harness_failure(rep_dir: Path) -> str | None:
    """Was the agent PREVENTED from working in this archived run?

    Returns a description when the run shows a harness failure rather than a model
    failure, else None.

    The disqualifying signature is **the agent produced no source files** — a model
    that merely *can't* do the task still writes something, so writing nothing points
    at the harness (a blocked/mis-pathed file tool, or a serving layer that never
    returns tool calls). That scores a zero indistinguishable from incapability,
    which is how a harness bug once masqueraded as a language "capability wall".

    A tool **refusal** in the log is corroborating evidence, not sufficient on its
    own: a resilient model routes around a blocked ``write_file`` via the shell and
    still ships working code. Refusals are therefore only reported alongside a run
    that produced nothing.
    """
    from retort.playpen.local_runner import _TOOL_REFUSAL_RE

    _SKIP = {
        "TASK.md", "stack.json", "REQUIREMENTS.json", "_meta.json", "scores.json",
        "evaluation.md", "assessment.json", "findings.jsonl", "FEEDBACK.md",
        "_agent_stdout.log", "_agent_stderr.log", "README.md", "prompts.txt",
    }
    produced = [
        p for p in rep_dir.rglob("*")
        if p.is_file() and p.name not in _SKIP
        and not p.name.startswith(".")
        and "summary" not in p.parts and "data" not in p.parts
    ]
    if produced:
        return None  # it wrote code — judge it on the code, not the harness

    why = (
        "agent wrote NO source files — a model that cannot do the task still writes "
        "something. Suspect the harness before the model."
    )
    log = rep_dir / "_agent_stdout.log"
    if log.is_file():
        try:
            m = _TOOL_REFUSAL_RE.search(log.read_text(errors="replace"))
        except OSError:
            m = None
        if m:
            why += (
                f" Its file tool was REFUSED: {m.group(0).strip()[:80]!r} — check "
                "playpen_root (must not sit under the system temp dir)."
            )
    return why


def _archive_run_workspace(
    archive_root: Path,
    run_config: dict[str, str],
    replicate: int,
    artifacts,
    visibility: str = "private",
    replace_existing: bool = False,
) -> Path | None:
    """Copy a run's workspace into the archive so it survives /tmp cleanup.

    Layout: <archive_root>/<sorted-factor=value-pairs>/rep<N>[ -failed]/

    Writes ``_meta.json`` next to the copied workspace so downstream tooling
    (report web, file-run-issues) can read the experiment's visibility level
    without re-parsing workspace.yaml. Returns the archived destination path
    (or None if archival was skipped or failed).
    """
    import shutil

    src = getattr(artifacts, "output_dir", None)
    if not src:
        return None
    src = Path(src)
    if not src.exists():
        return None

    cell_name = "_".join(f"{k}={v}" for k, v in sorted(run_config.items()))
    suffix = "" if artifacts.succeeded else "-failed"
    dest = archive_root / cell_name / f"rep{replicate}{suffix}"
    if dest.exists():
        if replace_existing and suffix == "":
            # A prior attempt (the pre-retry run, or the second-chance's first
            # attempt) already occupies rep<N>. Without this the archive step
            # early-returned and kept the OLD workspace while the DB recorded the
            # RETRY's scores — a passing row over an empty/failed archive (#42).
            # Preserve the prior attempt as rep<N>-failed (evidence + diagnose),
            # then fall through to archive the attempt whose scores we persist.
            failed_dest = archive_root / cell_name / f"rep{replicate}-failed"
            if failed_dest.exists():
                shutil.rmtree(failed_dest, ignore_errors=True)
            try:
                dest.rename(failed_dest)
            except OSError:
                shutil.rmtree(dest, ignore_errors=True)
        else:
            # Already archived (idempotent on resume of an in-progress run).
            return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    # repo-pr mode: the workspace is a git WORKTREE of a large base repo, so
    # copytree-ing it would archive the whole repo per attempt — exactly what this
    # mode exists to avoid. The deliverable is the DIFF, so archive
    # `attempt.patch` (+ the logs/meta needed for diagnosis) and nothing else.
    patch = src / "attempt.patch"
    if patch.is_file() and (src / ".git").exists():
        try:
            dest.mkdir(parents=True, exist_ok=True)
            for name in ("attempt.patch", "TASK.md", "stack.json", "scores.json",
                         "_agent_stdout.log", "_agent_stderr.log",
                         "_hermes_session.jsonl", ".hermes_usage.json"):
                f = src / name
                if f.is_file():
                    shutil.copy2(f, dest / name)
        except Exception as exc:  # never let archival abort the experiment
            click.echo(f"  (repo-pr archive failed for {cell_name} rep{replicate}: {exc})",
                       err=True)
            return None
    else:
        try:
            # Archive source + tests only. Build output and vendored dependencies
            # are regenerable and actively harmful in the archive: they bloat the
            # repo, embed third-party files that trip secret scanners (e.g. a
            # password fixture inside node_modules), and contain dangling build
            # symlinks (erlang `_build`) that otherwise abort the copy. Scoring
            # already ran against the live playpen and the spec eval reads source,
            # so none of this is needed here.
            shutil.copytree(
                src, dest,
                ignore=_ignore_archive_noise,
                ignore_dangling_symlinks=True,
            )
        except Exception as exc:  # don't let archival failure abort the experiment
            click.echo(f"  (archive failed for {cell_name} rep{replicate}: {exc})",
                       err=True)
            return None

    meta = {
        "visibility": visibility,
        "run_config": run_config,
        "replicate": replicate,
        "succeeded": artifacts.succeeded,
    }
    try:
        (dest / "_meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    except Exception as exc:
        click.echo(f"  (meta write failed for {cell_name} rep{replicate}: {exc})", err=True)
    return dest


def _seed_repair_workspace(env_dir: Path, prior, requirements_path: Path | None) -> None:
    """Seed a provisioned playpen with a prior attempt's code + a FEEDBACK.md so
    the agent repairs rather than rebuilds. TASK.md (written by provision) stays.
    """
    import shutil as _shutil

    skip = {"TASK.md", "stack.json", "scores.json", "assessment.json", "evaluation.md",
            "findings.jsonl", "_meta.json", ".coverage", "FEEDBACK.md", "REQUIREMENTS.json"}
    # The SAME noise filter as archiving, applied to the item ITSELF. copytree's
    # `ignore` callback only filters a directory's CHILDREN, so passing it alone
    # still copies `.build/` as the root of the copy — which is precisely the
    # directory that must not travel. Measured on exp-60's swift cell: the code
    # compiles clean in 2.9s, but the repair playpen inherited attempt 1's
    # .build, whose ModuleCache hard-codes attempt 1's playpen path, so attempt
    # 2 could never build and every metric recorded 0.0. A second chance that
    # cannot compile is not a second chance.
    noise = _ignore_archive_noise(str(prior["dir"]),
                                  [i.name for i in prior["dir"].iterdir()])
    for item in prior["dir"].iterdir():
        if item.name in skip or item.name in noise or item.name.startswith("_"):
            continue
        dst = env_dir / item.name
        try:
            if item.is_dir():
                # SAME filter as archiving. Without it the second chance
                # inherits the first attempt's build output — and a build tree
                # that hard-codes its own absolute path cannot survive the move
                # to a new playpen. Measured on exp-60's swift cell: the agent's
                # code compiles clean in 2.9s, but its second attempt was seeded
                # with attempt 1's .build and could never build again, so every
                # metric recorded 0.0. A repair attempt that cannot compile is
                # not a second chance, it is a guaranteed failure.
                _shutil.copytree(item, dst, dirs_exist_ok=True,
                                 ignore=_ignore_archive_noise)
            else:
                _shutil.copy2(item, dst)
        except OSError:
            pass
    # Build FEEDBACK.md: the requirement checklist + the prior evaluation verdict.
    lines = [
        "# Evaluation feedback on your previous attempt",
        "",
        "A previous attempt is already in this directory. It did NOT pass an "
        "independent evaluation. Fix it.",
        "",
        "## Requirements that must ALL be met",
    ]
    reqs = {}
    if requirements_path and Path(requirements_path).exists():
        try:
            reqs = json.loads(Path(requirements_path).read_text())
        except (OSError, ValueError):
            reqs = {}
    for rq in reqs.get("requirements", []):
        lines.append(f"- [{rq.get('id','')}] {rq.get('requirement','')}"
                     + (f"  (verify: {rq['how_to_verify']})" if rq.get("how_to_verify") else ""))
    lines += ["", "## What went wrong last time"]
    if prior["status"] == "crashed":
        lines.append("- The previous run never finished a testable build. Make sure the "
                     "project builds and the tests actually run and terminate.")
    else:
        rc = f", requirement_coverage {prior['req_cov']:.2f}" if prior["req_cov"] is not None else ""
        lines.append(f"- The build/tests did not fully pass (status: {prior['status']}{rc}).")
    findings_file = prior["dir"] / "assessment.json"
    if findings_file.exists():
        try:
            for f in json.loads(findings_file.read_text()).get("top_findings", [])[:10]:
                lines.append(f"- {f.get('title') or f.get('description') or f}")
        except (OSError, ValueError):
            pass
    # Golden-answer failures, with the specific wrong number and how to fix it.
    # Without this the repair attempt is told only "you failed"; with it the
    # agent is told "Flamengo shows 76 played, expected 38, deduplicate on
    # (date, home, away)" — which is the whole point of gating on facts.
    factual = prior["dir"] / "_factual.json"
    if factual.exists():
        try:
            from retort.scoring.scorers.factual_accuracy import Assertion, FactualResult
            raw = json.loads(factual.read_text())
            fr = FactualResult(ok=raw.get("ok", False), note=raw.get("note", ""),
                               assertions=[Assertion(**a) for a in raw.get("assertions", [])])
            lines += fr.feedback_lines()
        except (OSError, ValueError, TypeError):
            pass
    lines += ["", "Fix the existing code so every requirement above is met and the tests run and pass."]
    (env_dir / "FEEDBACK.md").write_text("\n".join(lines))
    if requirements_path and Path(requirements_path).exists():
        try:
            _shutil.copy2(requirements_path, env_dir / "REQUIREMENTS.json")
        except OSError:
            pass
    # Prompt-agnostic repair instruction: prepend a banner to TASK.md so the
    # agent repairs the seeded code and reads FEEDBACK.md whatever prompt the
    # experiment uses (needed for the default in-line second chance, which keeps
    # the experiment's own prompt).
    task_md = env_dir / "TASK.md"
    banner = (
        "# REPAIR TASK\n\nA previous attempt at the task below is ALREADY in this "
        "directory but did NOT pass an independent evaluation. Read `FEEDBACK.md` "
        "for exactly what was wrong, then FIX the existing code so it builds, all "
        "tests run and pass, and every requirement is met. Do NOT start over.\n\n"
        "---\n\n"
    )
    try:
        orig = task_md.read_text() if task_md.exists() else ""
        task_md.write_text(banner + orig)
    except OSError:
        pass


def _repair_prior_run(base: str, language: str, replicate: int):
    """For --repair-from: find the base experiment's prior attempt for this
    (language, replicate). Returns ``{'dir', 'status', 'req_cov'}`` for a
    REPAIRABLE prior (it failed/crashed AND left a code archive), or ``None``
    when there is nothing to repair (no prior, no code, or it already passed).
    """
    import glob as _glob
    import sqlite3 as _sqlite

    base_path = Path(base)
    db_path = base_path if base_path.suffix == ".db" else base_path / "retort.db"
    runs_root = (base_path.parent if base_path.suffix == ".db" else base_path) / "runs"
    if not db_path.exists():
        return None
    con = _sqlite.connect(db_path)
    con.row_factory = _sqlite.Row
    status = None
    req_cov = None
    for r in con.execute("SELECT id, status, replicate, run_config_json FROM experiment_runs"):
        try:
            cfg = json.loads(r["run_config_json"])
        except (TypeError, ValueError):
            continue
        if cfg.get("language") != language or r["replicate"] != replicate:
            continue
        status = r["status"]
        row = con.execute(
            "SELECT value FROM run_results WHERE run_id=? AND metric_name='requirement_coverage'",
            (r["id"],),
        ).fetchone()
        req_cov = row[0] if row else None
        break
    con.close()
    if status is None:
        return None
    # already passed → nothing to repair
    if status == "completed" and req_cov is not None and abs(req_cov - 1.0) < 1e-9:
        return None
    # Locate the archived code dir for this (language, replicate). The rep dir is
    # NOT always a direct child of the `*language=X*` cell dir: a model id with a
    # slash (mlxlocal/mlx-community--…) nests it one level deeper
    # (…language=rust_model=mlxlocal/mlx-community--…_stack=m80/rep2). Recurse with
    # `**` (matches zero-or-more segments, so the flat layout still matches) and
    # take the SHALLOWEST hit, so a stray `repN` inside the code tree can't win.
    matches = _glob.glob(
        str(runs_root / f"*language={language}*" / "**" / f"rep{replicate}"),
        recursive=True,
    )
    prior_dir = next(
        (Path(m) for m in sorted(matches, key=len) if Path(m).is_dir()), None
    )
    if prior_dir is None:
        return None
    # must contain some source to seed
    has_code = any(
        not f.name.startswith("_")
        and f.name not in ("TASK.md", "stack.json", "scores.json", "assessment.json",
                            "evaluation.md", "findings.jsonl", "_meta.json", "REQUIREMENTS.json")
        for f in prior_dir.rglob("*") if f.is_file()
    )
    if not has_code:
        return None
    return {"dir": prior_dir, "status": status, "req_cov": req_cov}
