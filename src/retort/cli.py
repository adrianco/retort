"""Retort CLI entry point."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from retort import __version__
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignMatrix, generate_design
# Split out of this file by concern (see retort/run/). Re-exported so the
# `cli._name` references in commands/ and tests -- and monkeypatching through
# this module -- keep resolving. Same pattern as the commands/ imports below.
from retort.run.liveness import (  # noqa: F401
    _etime_to_seconds,
    _retort_run_pids_for,
    _live_context_tokens,
    _discover_active_runs,
    _run_in_flight,
)
from retort.run.persist import (  # noqa: F401
    _factor_match_sql,
    _is_rep_dir,
    _run_config_from_cell_name,
    _iter_archive_cells,
    _run_row_exists,
    _run_has_requirement_coverage,
    _run_completed_exists,
    _factual_gate_failed,
    _init_database,
    _persist_design_matrix,
    _persist_metric_values,
    _persist_requirement_coverage,
    _persist_judge_attempt,
    _persist_rescore,
    _store_run_result,
)
from retort.run.workspace import (  # noqa: F401
    _ignore_archive_noise,
    _gitignore_for,
    _harness_failure,
    _archive_run_workspace,
    _seed_repair_workspace,
    _repair_prior_run,
)
from retort.run.evaluate import (  # noqa: F401
    _is_auth_failure,
    _find_skill,
    _evaluation_is_current,
    _shortfalls_claimed,
    _tests_did_not_run,
    _read_requirement_coverage,
    _declutter_for_eval,
    _build_challenge,
    _eval_tooling_preflight,
    _generate_requirements_from_prompt,
    _ensure_requirements_json,
    _invoke_claude_skill_prompt,
    _invoke_claude_skill,
    _invoke_judge_prompt,
    _run_auto_evaluation,
    _spec_conformance_passes,
)

WORKSPACE_TEMPLATE = """\
# Retort workspace configuration
# See docs/configuration.md for full reference

experiment:
  name: __NAME__
  # visibility: public  -> runs/ and reports/web/ are git-tracked and safe to publish
  # visibility: private -> all artifacts stay local; nothing leaks
  # Default is "private" (fail-closed). Opt into public explicitly.
  visibility: __VISIBILITY__

factors:
  language:
    levels: [python, typescript, go]
  agent:
    levels: [claude-code, qwen-local, pi-dense]
  thinking:
    levels: [off, minimal]
  framework:
    levels: [fastapi, nextjs, stdlib]

responses:
  - code_quality
  - token_efficiency
  - test_coverage
  # Starts the produced program and times it, for every language that has a
  # probe. Runs inline while the playpen is still built — archives have
  # build/target/node_modules stripped, so this cannot be recovered afterwards
  # by re-scoring. Runs it cannot measure are recorded as NULL, not 0.
  # See docs/runtime-measurement.md.
  - runtime
  # Asks the finished server questions with externally-verifiable answers and
  # GATES on them: a run can implement every checklist item and still get the
  # numbers wrong. Failures are fed to the self-repair second chance with the
  # specific wrong figure. No-op (1.0) for tasks that have no golden answers.
  - factual_accuracy
  # NOTE: `build_time` was removed — use the `_duration_seconds` telemetry
  # written automatically by every run instead.

tasks:
  - source: bundled://rest-api-crud

playpen:
  runner: docker
  replicates: 3
  timeout_minutes: 30
  local_agents:
    qwen-local:
      harness: omp
      model: moe
    pi-dense:
      harness: omp
      model: dense

design:
  screening_resolution: 3
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }

evaluation:
  enabled: true
  model: haiku
  min_severity_to_file: high
  issue_tracker: beads
"""


@click.group()
@click.version_option(version=__version__, prog_name="retort")
def main() -> None:
    """Retort — Platform Evolution Engine.

    Distill the best from the combinatorial mess.
    """


def _ordered_runs(run_configs, reps, reload_key_fn=None):
    """Yield ``(rep, run_idx, run_config)`` in execution order.

    ``run_idx`` is always the cell's index in the design (stable labels/sharding).

    - **No reload key** (default): plain replicate-major — one full pass over
      every cell per replicate. Interrupted/sharded runs get complete factor
      coverage first at lower replication.
    - **Reload key set**: group all runs sharing a key (the reload-triggering
      ``stack`` factor) contiguously so the serving stack is (re)loaded once per
      group, keeping replicate-major *within* each group. Group order follows
      each key's first appearance in the design (so a stack-sorted design is
      honoured). Turns N_stacks × reps reloads into N_stacks.
    """
    indexed = list(enumerate(run_configs))
    if reload_key_fn is None:
        for rep in range(1, reps + 1):
            for run_idx, run_config in indexed:
                yield rep, run_idx, run_config
        return
    groups: dict = {}
    for run_idx, run_config in indexed:
        groups.setdefault(reload_key_fn(run_config), []).append((run_idx, run_config))
    for members in groups.values():
        for rep in range(1, reps + 1):
            for run_idx, run_config in members:
                yield rep, run_idx, run_config


# Paths whose contents are sensitive in private mode (must be ignored).
_PRIVATE_SENSITIVE_PATHS = (
    "runs",
    "reports",
    "evaluation.md",
    "findings.jsonl",
    "TASK.md",
)


@main.group()
def design() -> None:
    """Design matrix generation commands."""


def _load_factors(config_path: str | None) -> FactorRegistry:
    """Load factors from a YAML config file or JSON stdin."""
    if config_path is not None:
        return _load_from_yaml(config_path)
    else:
        return _load_from_stdin()


def _load_from_yaml(path: str) -> FactorRegistry:
    """Load factors from a workspace YAML file."""
    try:
        import yaml
    except ImportError:
        click.echo(
            "Error: pyyaml required for --config. Install with: pip install pyyaml",
            err=True,
        )
        sys.exit(1)

    with open(path) as f:
        data = yaml.safe_load(f)

    factors_spec = data.get("factors", {})
    if not factors_spec:
        click.echo(f"Error: no 'factors' key found in {path}", err=True)
        sys.exit(1)

    registry = FactorRegistry()
    for name, spec in factors_spec.items():
        levels = spec if isinstance(spec, list) else spec.get("levels", [])
        registry.add(name, levels)
    return registry


def _load_from_stdin() -> FactorRegistry:
    """Load factors from JSON on stdin."""
    if sys.stdin.isatty():
        click.echo(
            "Error: no --config provided and stdin is a TTY. "
            "Pipe JSON factor spec or use --config.",
            err=True,
        )
        sys.exit(1)

    data = json.load(sys.stdin)
    return FactorRegistry.from_dict(data)


@main.command("run")
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    required=True,
    help="Experiment phase to execute.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config.",
)
@click.option(
    "--task",
    "task_source",
    type=str,
    default=None,
    help="Task source URI (e.g., bundled://rest-api-crud). Defaults to first task in config.",
)
@click.option(
    "--replicates",
    type=int,
    default=None,
    help="Override number of replicates per design point.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be run without executing.",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Skip cells already completed in the workspace database. Use to continue an interrupted experiment.",
)
@click.option(
    "--retry-failed",
    is_flag=True,
    help="With --resume, also re-run `failed` DATA-POINT cells (agent completed "
         "but fell short of a gate) to re-measure them. Note: `crashed` cells "
         "(agent never completed) are ALWAYS re-run on --resume regardless.",
)
@click.option(
    "--shard",
    type=str,
    default=None,
    help=(
        "Run only a slice of the design: 'INDEX/TOTAL' (e.g. '0/4' takes the "
        "1st of 4 shards). Each (run, replicate) pair is hashed deterministically "
        "to a shard. Combine with --resume on a shared retort.db so multiple "
        "polecats can run in parallel without colliding."
    ),
)
@click.option(
    "--design",
    "design_csv",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Path to a CSV design matrix produced by `retort design generate -o`. "
        "When provided, skips auto-generation and runs exactly the cells listed "
        "in the file. Use this to run a manually-trimmed fractional design. "
        "Overrides the workspace design.fraction setting."
    ),
)
@click.option(
    "--install-toolchains/--no-install-toolchains",
    "install_toolchains",
    default=None,
    help=(
        "Override playpen.auto_install_toolchains: install (or skip installing) "
        "the build/test toolchains the language factor needs (go, cargo, dotnet, "
        "…) before running. Defaults to the workspace config."
    ),
)
@click.option(
    "--repair-from",
    type=click.Path(exists=True),
    default=None,
    help=(
        "SELF-REPAIR mode. Path to a base experiment dir (or its retort.db). For "
        "each (language, replicate) cell, seed the playpen with that cell's prior "
        "attempt from the base experiment, drop in a FEEDBACK.md (requirement "
        "checklist + the prior evaluation verdict), and let the agent fix it — "
        "instead of building from scratch. Cells whose prior attempt already "
        "passed are skipped. Use a `prompt: [repair]` factor with a "
        "prompts/repair.md that tells the agent to read FEEDBACK.md and repair the "
        "existing code. Produces a normal retort.db, scored/gated like any run."
    ),
)
@click.option(
    "--no-second-chance",
    is_flag=True,
    default=False,
    help=(
        "Disable the DEFAULT self-repair second chance. By default, when a cell "
        "fails the gate (agent completed but fell short), it gets ONE repair "
        "attempt — re-seeded with its own code + FEEDBACK.md — before being "
        "recorded; a run that only passes on the second try is a `_second_try` run "
        "counted at HALF credit toward pass-proportion. Use this to turn that off "
        "(e.g. to avoid doubling paid-model cost on failures). Crashes are never "
        "second-chanced (nothing to repair); they retry via --resume."
    ),
)
def run_experiments(
    phase: str,
    config: str,
    task_source: str | None,
    replicates: int | None,
    dry_run: bool,
    resume: bool,
    retry_failed: bool,
    shard: str | None,
    design_csv: str | None,
    install_toolchains: bool | None,
    repair_from: str | None,
    no_second_chance: bool,
) -> None:
    """Execute experiment runs for a design matrix.

    Generates the design, provisions playpens, executes each run,
    scores the results, and stores everything in the workspace database.
    """
    import yaml as _yaml

    from retort.config.loader import load_workspace
    from retort.playpen.docker_runner import DockerRunner
    from retort.playpen.local_runner import LocalRunner
    from retort.playpen.runner import StackConfig
    from retort.playpen.task_loader import load_task, task_requirements_path
    from retort.scoring.collector import ScoreCollector
    from retort.storage.database import create_tables, get_engine, get_session

    # Load workspace config
    workspace_config = load_workspace(config)

    # Build factor registry
    registry = FactorRegistry()
    for name, factor in workspace_config.factors.items():
        registry.add(name, factor.levels)

    if len(registry) < 2:
        raise click.ClickException("Need at least 2 factors for experiment runs.")

    # Languages whose build/test toolchain the run will need (for the preflight).
    _lang_factor = workspace_config.factors.get("language") or workspace_config.factors.get("languages")
    languages = list(_lang_factor.levels) if _lang_factor else []
    do_install_toolchains = (
        workspace_config.playpen.auto_install_toolchains
        if install_toolchains is None
        else install_toolchains
    )

    if retry_failed and not resume:
        raise click.ClickException("--retry-failed requires --resume.")

    shard_index, shard_total = _parse_shard(shard)

    # Generate (or load) design matrix
    if design_csv is not None:
        design = DesignMatrix.from_csv(design_csv, phase)
        click.echo(f"Design matrix: {design.num_runs} runs (loaded from {design_csv})")
    else:
        fraction = workspace_config.design.fraction
        design = generate_design(registry, phase, fraction=fraction)
        if fraction is not None and fraction < 1.0:
            full_n = design.full_factorial_size or design.num_runs
            click.echo(
                f"Design matrix: {design.num_runs}/{full_n} cells "
                f"({fraction:.0%} fraction, {phase})"
            )
        else:
            click.echo(f"Design matrix: {design.num_runs} runs ({phase})")

    # Resolve task
    if task_source is None:
        task_source = workspace_config.tasks[0].source
    task = load_task(task_source)
    click.echo(f"Task: {task.name}")

    # Determine replicates
    reps = replicates or workspace_config.playpen.replicates
    total_runs = design.num_runs * reps
    click.echo(f"Replicates: {reps} ({total_runs} total runs)")

    # Initialize database (needed early so --resume can inspect existing runs
    # before dry-run reports what would actually execute).
    config_dir = Path(config).resolve().parent
    db_path = config_dir / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)

    # Archive root: per-run workspaces are copied here so artifacts survive
    # /tmp cleanup and process kills.
    archive_root = config_dir / "runs"
    archive_root.mkdir(exist_ok=True)

    # Guarantee a pinned requirement checklist for the spec gate. Without it the
    # evaluate-run skill silently falls back to ad-hoc TASK.md extraction, so
    # requirement_coverage uses a varying denominator and isn't comparable
    # across runs/experiments. Copy the task's canonical REQUIREMENTS.json, or
    # generate one from the prompt (and warn) so every experiment has one.
    _ensure_requirements_json(config_dir, task, task_source, task_requirements_path)

    # Persist the design matrix so downstream `retort report effects --matrix-id`
    # can join run results back to factor levels. Idempotent on resume — looks
    # up by (matrix name + phase) and reuses if found.
    design_session = get_session(engine)
    try:
        matrix_id, run_config_to_row_id = _persist_design_matrix(
            design_session, registry, design, phase, workspace_config,
        )
        design_session.commit()
    except Exception:
        design_session.rollback()
        raise
    finally:
        design_session.close()

    # Build set of (run_config_json, replicate) pairs to skip when resuming.
    skip_keys: set[tuple[str, int]] = set()
    if resume:
        from retort.storage.models import ExperimentRun, RunStatus

        existing_session = get_session(engine)
        try:
            # Skip cells that already hold a DATA POINT: `completed` (passed) and
            # `failed` (ran to completion but fell short of a gate — a genuine
            # measurement). `crashed` rows are never skipped, so a cell whose
            # agent never completed is always re-attempted on --resume.
            # --retry-failed additionally re-runs the `failed` data points (to
            # re-measure genuine failures, e.g. after a fix or for more samples).
            statuses = [RunStatus.completed]
            if not retry_failed:
                statuses.append(RunStatus.failed)
            for row in existing_session.query(
                ExperimentRun.run_config_json, ExperimentRun.replicate
            ).filter(ExperimentRun.status.in_(statuses)).all():
                # Normalize JSON key ordering so config dicts match regardless
                # of how they were serialized originally.
                try:
                    normalized = json.dumps(json.loads(row[0]), sort_keys=True)
                except (TypeError, ValueError):
                    normalized = row[0]
                skip_keys.add((normalized, row[1]))
        finally:
            existing_session.close()
        if skip_keys:
            click.echo(f"Resume: {len(skip_keys)} run(s) already recorded — will skip.")

    # Reload-minimising order. Computed HERE rather than at the execution loop so
    # the dry-run preview below and the real run below that are driven by the SAME
    # value — the preview used to render a naive replicate-major order regardless,
    # which is a lie precisely where it matters: `--dry-run` is what you reach for
    # to check sequencing, and it showed m35/m80/m35/m80 (a reload per cell) for a
    # design the runner actually executes grouped (one reload per stack).
    _reload_key_fn = None
    if workspace_config.playpen.runner == "local" and workspace_config.playpen.stack_presets:
        _reload_key_fn = lambda rc: rc.get("stack")  # noqa: E731

    # A `tooling: graphify` cell whose agent never opened the graph is a
    # `tooling: none` cell wearing a label, and its null is worthless. The
    # detector for that is `graph_usage_score` — but ScoreCollector runs ONLY the
    # metrics named in `responses:`, so a workspace that varies graphify without
    # listing it silently skips the one check that makes the arm interpretable.
    # (This bit the project once already at a level below: agent_consulted() had
    # the right semantics and a docstring naming this use, and was wired to
    # nothing but a test.)
    _tooling_levels = {
        (rc.get("tooling") or "none") for rc in design.run_configs()
    }
    if "graphify" in _tooling_levels and "graph_usage_score" not in [r.name for r in workspace_config.responses]:
        click.echo(
            "⚠️  This design varies `tooling: graphify` but `responses:` does not "
            "include `graph_usage_score`.\n"
            "    Without it nothing records whether the agent actually CONSULTED "
            "the graph, and a\n"
            "    graphify cell that ignored it is indistinguishable from "
            "`tooling: none` — so a null\n"
            "    result would be unfalsifiable. Add it to `responses:`.",
            err=True,
        )

    if dry_run:
        click.echo("\n[dry-run] Design matrix:")
        if shard_total > 1:
            click.echo(f"Shard: {shard_index}/{shard_total} — only owned cells run.")
        if _reload_key_fn is not None:
            click.echo("Order: grouped by stack — each serving stack loads once.")
        will_run = 0
        will_skip = 0
        will_other_shard = 0
        for rep, i, run_config in _ordered_runs(design.run_configs(), reps, _reload_key_fn):
            config_key = json.dumps(run_config, sort_keys=True)
            if not _shard_owns(config_key, rep, shard_index, shard_total):
                will_other_shard += 1
                click.echo(f"  [shrd] Run {i+1} rep {rep}: {run_config}")
                continue
            marker = "skip" if (config_key, rep) in skip_keys else "RUN "
            if marker == "skip":
                will_skip += 1
            else:
                will_run += 1
            click.echo(f"  [{marker}] Run {i+1} rep {rep}: {run_config}")
        msg = f"\nWould execute {will_run} runs ({will_skip} skipped"
        if shard_total > 1:
            msg += f", {will_other_shard} owned by other shards"
        msg += "). Exiting."
        click.echo(msg)
        if languages and workspace_config.playpen.runner == "local":
            from retort.playpen.toolchains import ensure_toolchains, format_report

            statuses = ensure_toolchains(languages, install=False)
            click.echo("\n[dry-run] Toolchain preflight (no install):")
            for line in format_report(statuses, installed_action=False):
                click.echo(line)
        engine.dispose()
        return

    # Disk-space preflight. A run writes a fresh playpen per cell (a full app +
    # its build tree — node_modules/target can be GB each) and the local serving
    # layer keeps a paged-SSD KV cache that grows to its configured cap. On a
    # near-full disk the agent's writes fail and the run scores false zeros
    # (indistinguishable from an incapable model), or oMLX degrades. Fail fast.
    import shutil as _shutil
    _playpen_root = os.path.expanduser(
        str(getattr(workspace_config.playpen, "playpen_root", "") or "~/.retort/work")
    )
    _probe = _playpen_root if os.path.isdir(_playpen_root) else os.path.expanduser("~")
    _free_gb = _shutil.disk_usage(_probe).free / 2**30
    if _free_gb < 5:
        raise click.ClickException(
            f"Low disk: only {_free_gb:.0f} GB free at {_probe}. An experiment writes "
            f"large per-cell playpens and a growing serving cache; a near-full disk scores "
            f"false zeros. Free space first (clear ~/.cache/omlx-ssd, ~/.retort/work, and "
            f"thin local snapshots: `tmutil thinlocalsnapshots / 100000000000 4`), then re-run."
        )
    if _free_gb < 15:
        # The hard floor was 15 GB until PR #45 lowered it to 5 for a constrained
        # VM. That is a reasonable need, but 5–15 GB is precisely where a run
        # completes and scores FALSE ZEROS rather than failing outright — the
        # failure mode this project keeps having to un-publish. So the band that
        # used to abort now warns in its own right, naming the risk.
        click.echo(
            f"⚠️  Disk preflight: only {_free_gb:.0f} GB free at {_probe}. This is BELOW the "
            f"level that used to abort a run. A run can still complete here and score false "
            f"zeros when the playpen or serving cache fills mid-way — treat any all-zero "
            f"cell from this run as suspect and check disk before believing it.",
            err=True,
        )
    elif _free_gb < 40:
        click.echo(
            f"⚠️  Disk preflight: {_free_gb:.0f} GB free at {_probe} — low; a long run may "
            f"fill it (the oMLX paged-SSD cache grows to its cap). Consider clearing caches.",
            err=True,
        )
    else:
        click.echo(f"Disk preflight: {_free_gb:.0f} GB free — ok.")

    # Toolchain preflight — ensure the build/test toolchain each language factor
    # level needs is present, installing missing ones when enabled. Best-effort:
    # failures warn but never abort (scorers already skip on a missing tool), so
    # a run is never worse off than without this step.
    if languages and workspace_config.playpen.runner == "local":
        from retort.playpen.toolchains import ensure_toolchains, format_report

        if do_install_toolchains:
            click.echo("Toolchain preflight (installing missing toolchains):")
        else:
            click.echo("Toolchain preflight (check only — auto-install disabled):")
        statuses = ensure_toolchains(languages, install=do_install_toolchains)
        for line in format_report(statuses, installed_action=do_install_toolchains):
            click.echo(line)

    # Set up runner and scorer
    runner_type = workspace_config.playpen.runner
    if runner_type == "local":
        prompts_dir = config_dir / "prompts"
        stack_manager = None
        if workspace_config.playpen.stack_presets:
            from retort.playpen.stack_reload import make_stack_manager
            registry_path = config_dir / workspace_config.playpen.stack_presets
            # backend (oMLX / llama.cpp) is chosen by serving.backend in the registry
            stack_manager = make_stack_manager(registry_path)
            # Make Hermes' turn cap agree with the one this workspace declares.
            # Hermes reads max_turns from its config file (no CLI flag), so
            # without this it runs at whatever the file last said — which was 30,
            # while workspaces declared 200. Runs needing more were silently
            # truncated and scored as model failures.
            stack_manager.agent_max_turns = workspace_config.playpen.max_turns

        # Local-agent binary preflight. A configured local agent whose CLI can't
        # be resolved crashes EVERY cell that uses it at 0.0s ("Agent CLI not
        # found"), which is indistinguishable from a model that produced nothing —
        # a harness failure masquerading as a model result. Check up front and
        # warn with the concrete fix, before a single cell is burned.
        _local_agents = workspace_config.playpen.local_agents or {}
        if _local_agents:
            import os as _os
            import shutil as _sh

            _serving = getattr(stack_manager, "serving", {}) or {}

            def _agent_cli(_name: str, _spec) -> str:
                # _spec is a LocalAgentConfig (pydantic), not a dict — use getattr.
                # A profile-level `bin` wins over the stack-level serving value —
                # mirrors local_runner's spawn-site precedence so the preflight
                # checks the executable that will actually run.
                _pb = getattr(_spec, "bin", None)
                if _pb:
                    return _pb
                _harness = getattr(_spec, "harness", None) or _name
                if _harness == "hermes":
                    return _serving.get("hermes_bin", "hermes")
                return _harness  # omp / gemini / opencode / codex use their CLI name

            _missing: list[tuple[str, str]] = []
            for _an, _spec in _local_agents.items():
                _bin = _agent_cli(_an, _spec)
                _ok = _bin if (_os.path.isabs(_bin) and _os.path.exists(_bin)) else _sh.which(_bin)
                if _ok is None:
                    _missing.append((_an, _bin))
            if _missing:
                click.echo("Local-agent preflight:")
                for _an, _bin in _missing:
                    _hint = (
                        f" — set serving.hermes_bin in {workspace_config.playpen.stack_presets} "
                        "to the hermes binary's path"
                        if _bin == "hermes"
                        else f" — install it or put '{_bin}' on PATH"
                    )
                    click.echo(
                        f"  ⚠ agent '{_an}': CLI '{_bin}' not found{_hint}. "
                        "Every cell using it will crash at 0.0s."
                    )
            else:
                click.echo(f"Local-agent preflight: {len(_local_agents)} agent(s) OK.")

        # JUDGE PREFLIGHT. `_eval_tooling_preflight` already existed for this
        # exact purpose but was only wired into rescore/reevaluate, never into a
        # RUN — so an experiment discovered a dead judge one cell at a time and
        # recorded every cell with requirement_coverage NULL. That is worse than
        # crashing: the data looks complete and cannot be pooled with anything.
        # Costs one trivial prompt; saves a whole grid.
        if workspace_config.evaluation.enabled:
            _ok, _msg = _eval_tooling_preflight(
                getattr(workspace_config.evaluation, "model", None),
                config_dir / "runs",
            )
            if not _ok:
                raise click.ClickException(
                    f"JUDGE PREFLIGHT FAILED — {_msg}\n\n"
                    "  requirement_coverage is this project's primary response. "
                    "Running now would record every cell with it NULL, which "
                    "looks like complete data and silently cannot be pooled.\n"
                    "  If the judge is not authenticated, run `/login` at an "
                    "interactive terminal (local-only; it does not work over "
                    "Remote Control) and check with:\n"
                    "      claude -p 'Reply with exactly: OK'\n"
                    "  To run without a spec gate on purpose, set "
                    "`evaluation: {enabled: false}` — but see the standing note "
                    "that an ungated experiment is not comparable."
                )
            click.echo(f"Judge preflight: {_msg}")

        runner = LocalRunner(
            timeout_minutes=workspace_config.playpen.timeout_minutes,
            stall_minutes=workspace_config.playpen.stall_minutes,
            max_turns=workspace_config.playpen.max_turns,
            default_model=workspace_config.playpen.model,
            default_thinking=workspace_config.playpen.thinking,
            local_agents=workspace_config.playpen.local_agents,
            local_inference_cost=workspace_config.playpen.local_inference_cost,
            prompts_dir=prompts_dir if prompts_dir.is_dir() else None,
            stack_manager=stack_manager,
        )
    elif runner_type == "metaharness":
        from retort.playpen.metaharness_runner import MetaHarnessRunner
        runner = MetaHarnessRunner(
            timeout_minutes=workspace_config.playpen.timeout_minutes,
            max_turns=workspace_config.playpen.max_turns,
            default_model=workspace_config.playpen.model,
        )
    else:
        runner = DockerRunner(timeout_minutes=workspace_config.playpen.timeout_minutes)
    metric_names = [r.name for r in workspace_config.responses]
    collector = ScoreCollector(metrics=metric_names)


    # Fail fast: validate agent types before any runs start.
    if runner_type == "local":
        _supported_agents = {"claude-code", *workspace_config.playpen.local_agents}
        for _rc in design.run_configs():
            _agent = _rc.get("agent", "claude-code") or "claude-code"
            if _agent not in _supported_agents and _agent != "unknown":
                raise click.ClickException(
                    f"Agent {_agent!r} is not implemented. "
                    f"Only {sorted(_supported_agents)} are supported in this release. "
                    f"Remove or replace unsupported agent levels in your workspace config."
                )

    # Capture the FULL stack this experiment runs on — versions, model revisions,
    # sampling params, agent config, harness settings — and write it beside the
    # data. A pass-proportion is meaningless without the stack it was measured on:
    # every wrong conclusion so far (temp=1.0 sampling, the /var playpen the agent
    # couldn't write to, the omp-vs-hermes agent swap) came from a stack variable
    # nobody recorded. The manifest is a reported result, not a debug aid.
    try:
        from retort.reporting import provenance as _prov
        _presets = None
        if workspace_config.playpen.stack_presets:
            import yaml as _yaml
            _presets = (_yaml.safe_load(
                (config_dir / workspace_config.playpen.stack_presets).read_text()
            ) or {}).get("presets")
        _manifest = _prov.capture(
            repo=Path(__file__).resolve().parents[2],
            config_dir=config_dir,
            playpen_config=workspace_config.playpen,
            stack_presets=_presets,
            model_ids=[
                str(rc.get("model")) for rc in design.run_configs() if rc.get("model")
            ],
            # Which agents the design ACTUALLY runs, so provenance records the
            # stack that ran rather than every stack installed on the box.
            agents=sorted({str(rc.get("agent") or "claude-code")
                           for rc in design.run_configs()}),
        )
        _path = _prov.write(_manifest, config_dir)
        click.echo("\nStack provenance (recorded to %s):" % _path.name)
        for _line in _prov.summarize(_manifest):
            click.echo(_line)
    except Exception as _exc:  # noqa: BLE001 — provenance must never block a run
        click.echo(f"  (provenance capture failed: {_exc})", err=True)

    click.echo(f"\nStarting experiment runs...")

    completed = 0
    failed = 0
    crashed = 0
    skipped = 0
    accumulated_cost = 0.0
    accumulated_tokens = 0
    # Harness self-check: consecutive runs where the agent wrote no files at all.
    # A blocked file tool scores false zeros that mimic a model incapability, so a
    # streak of them stops the experiment instead of poisoning the data.
    no_write_streak = 0
    no_write_abort_after = workspace_config.playpen.no_write_abort_after
    cost_limit = workspace_config.playpen.cost_limit_usd
    token_limit = workspace_config.playpen.token_limit

    # Reload-minimising order. When a cell change forces an expensive serving-
    # stack reload (a `stack` factor driving stack_presets — sampling params or,
    # later, different model weights), group all runs sharing a stack contiguously
    # so each stack loads exactly ONCE, and keep replicate-major *within* the
    # group. Without a reload cost, fall back to plain replicate-major (full
    # coverage first at lower replication). See _ordered_runs.
    # _reload_key_fn is computed once, above the dry-run block, so the preview and
    # this loop can never disagree about execution order.

    session = get_session(engine)
    try:
        # Replicate-major order: complete one full pass over every design cell
        # (full factor coverage) before starting the next replicate. So an
        # interrupted, resumed, or incrementally-sharded run yields complete
        # coverage at lower replication rather than full replication of a few
        # cells. Replicate is the outer loop; the design cells are the inner.
        # (When a reload key is set, runs are grouped by stack first — see above.)
        for rep, run_idx, run_config in _ordered_runs(
            design.run_configs(), reps, _reload_key_fn
        ):
                stack = StackConfig.from_run_config(run_config)
                config_key = json.dumps(run_config, sort_keys=True)
                label = f"[{run_idx+1}/{design.num_runs} rep {rep}/{reps}]"
                if not _shard_owns(config_key, rep, shard_index, shard_total):
                    # Belongs to a different shard. Don't even mark it skipped —
                    # another polecat will pick it up.
                    continue
                if (config_key, rep) in skip_keys:
                    click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent} — skip (resume)")
                    skipped += 1
                    continue
                # Self-repair mode: only run cells whose prior attempt failed and
                # left code to fix; skip the rest (nothing to repair).
                repair_prior = None
                if repair_from is not None:
                    repair_prior = _repair_prior_run(repair_from, stack.language, rep)
                    if repair_prior is None:
                        click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent} — skip (no repairable prior)")
                        skipped += 1
                        continue
                click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent}", nl=False)

                estimated_timeout = _estimate_run_timeout(
                    session, run_config, workspace_config.playpen.timeout_minutes
                )
                if estimated_timeout != runner.timeout_minutes:
                    click.echo(f" [timeout={estimated_timeout}m]", nl=False)
                runner.timeout_minutes = estimated_timeout

                env_id = runner.provision(stack, task)
                if repair_prior is not None:
                    _seed_repair_workspace(
                        runner.work_dir / env_id, repair_prior,
                        config_dir / "REQUIREMENTS.json",
                    )
                try:
                    artifacts = runner.execute(env_id, stack, task)
                    if artifacts.usage_limited:
                        # Not a model failure — the agent never got to do the
                        # work. Leave this cell UNRECORDED so --resume re-runs it,
                        # and stop the run so the remaining cells aren't burned
                        # against the same exhausted limit. (teardown via finally)
                        click.echo(" — usage limit (not recorded)", err=True)
                        raise _UsageLimitStop()

                    # Harness self-check — STOP rather than record false zeros.
                    # A blocked file-write tool and a model that simply can't do
                    # the task are indistinguishable in the metrics (both produce
                    # no code, requirement_coverage 0). Recording those as model
                    # results is how a harness bug masquerades as a "capability
                    # wall" — it cost us ~10 experiments before it was caught.
                    #
                    # BUT only abort when the refusal actually blocked the work:
                    # the workspace must be byte-for-byte as seeded (wrote_nothing).
                    # Some agents (Hermes) emit a benign per-turn advisory —
                    # "File-mutation verifier: N file(s) were NOT modified this turn"
                    # — on any turn that happens not to write a file; that matches
                    # the refusal regex yet the run still produces a complete, passing
                    # implementation. Aborting on it discarded good 80B runs (exp-30).
                    _refusal = artifacts.metadata.get("tool_refusal")
                    if _refusal and artifacts.metadata.get("wrote_nothing") == "true":
                        raise click.ClickException(
                            f"HARNESS BROKEN — the agent's file tool was refused:\n"
                            f"    {_refusal}\n\n"
                            f"  Workspace: {artifacts.output_dir}\n"
                            f"  The agent could not write into its own playpen, so this "
                            f"run (and any like it) would score a FALSE ZERO that looks "
                            f"identical to a model that can't do the task.\n"
                            f"  Stopping so the harness can be fixed rather than "
                            f"recording garbage. Nothing was written for this cell; "
                            f"--resume will re-run it once fixed.\n"
                            f"  Known cause: playpens under a path the agent considers "
                            f"system-owned (e.g. macOS /var/folders). Playpens now live "
                            f"under ~/.retort/work."
                        )
                    if artifacts.metadata.get("wrote_nothing") == "true":
                        no_write_streak += 1
                        if (no_write_abort_after
                                and no_write_streak >= no_write_abort_after):
                            raise click.ClickException(
                                f"HARNESS SUSPECTED — {no_write_streak} consecutive runs "
                                f"wrote NO files at all.\n\n"
                                f"  Workspace: {artifacts.output_dir}\n"
                                f"  A model that can't do the task still *writes something*. "
                                f"Writing nothing, repeatedly, points at the harness (a "
                                f"blocked/mis-pathed file tool, a bad workspace, a serving "
                                f"layer that never returns tool calls) — not the model.\n"
                                f"  Stopping so it can be diagnosed rather than recording "
                                f"false zeros. Check the agent's stdout in the workspace "
                                f"(_agent_stdout.log). Set playpen.no_write_abort_after: 0 "
                                f"to disable this check."
                            )
                    else:
                        no_write_streak = 0

                    scores = collector.collect(artifacts, stack)

                    # Conformance gate: an agent-succeeded run whose tests never
                    # executed is not a valid success — record it as failed.
                    tests_failed = _tests_did_not_run(scores)

                    # Archive before teardown wipes the workspace. The spec gate
                    # below reads the archived code; the eval reads the just-
                    # computed mechanical scores from scores.json (the run isn't
                    # in the DB yet), so drop those alongside the code.
                    archived = _archive_run_workspace(
                        archive_root, run_config, rep, artifacts,
                        visibility=workspace_config.experiment.visibility,
                        # On --retry-failed this run supersedes a prior attempt's
                        # archive; replace it (preserving the old as rep<N>-failed)
                        # so the archive matches the scores we persist (#42).
                        replace_existing=retry_failed,
                    )
                    if archived is not None:
                        try:
                            (archived / "scores.json").write_text(json.dumps(scores.to_dict()))
                        except OSError:
                            pass

                    # Spec-conformance gate: a second-opinion eval (judge =
                    # evaluation.model) must confirm the code implements the
                    # task's requirements. Runs only when evaluation is enabled
                    # and the run is otherwise valid (agent succeeded + tests
                    # ran). The run fails only if two independent evals both
                    # fall short of full requirement coverage.
                    spec_failed = False
                    req_cov = None
                    if (workspace_config.evaluation.enabled
                            and artifacts.succeeded and not tests_failed
                            and archived is not None):
                        try:
                            spec_verdict, req_cov = _spec_conformance_passes(
                                archived,
                                workspace_config.evaluation,
                                workspace_config.experiment.visibility,
                                local_agents=workspace_config.playpen.local_agents,
                            )
                            # Only an explicit False (two real short opinions)
                            # fails the run; None (eval couldn't run) does not.
                            spec_failed = spec_verdict is False
                        except Exception as exc:
                            click.echo(f"  (spec gate crashed: {exc}; not gating)", err=True)

                    # Third gate: the answers must be RIGHT, not just present.
                    # A brazil run can implement every checklist item and still
                    # double-count the overlapping match files; requirement_coverage
                    # cannot see that, because it asks whether a capability exists.
                    # Scores below 1.0 mean a golden-answer assertion failed.
                    factual_failed = _factual_gate_failed(scores)
                    run_ok = (artifacts.succeeded and not tests_failed
                              and not spec_failed and not factual_failed)
                    # A run that never completed (agent crash / timeout kill /
                    # server unreachable) is not a data point — it is retried.
                    # A completed-but-gate-failed run IS a data point (progress).
                    run_crashed = not artifacts.succeeded

                    # DEFAULT self-repair: a gate-FAILURE (agent completed but fell
                    # short) gets ONE repair attempt, re-seeded with its own code +
                    # FEEDBACK.md. A crash has no artifact to repair; a --repair-from
                    # cell is already a repair. A second-try PASS is recorded like
                    # any run but flagged `_second_try` → HALF credit in analysis.
                    second_try = False
                    if (not run_ok and not run_crashed and not no_second_chance
                            and repair_from is None and archived is not None):
                        click.echo(" — 2nd chance…", nl=False)
                        # count the first attempt's spend toward the run totals
                        if artifacts.metadata:
                            try:
                                accumulated_cost += float(artifacts.metadata.get("total_cost_usd") or 0)
                            except (TypeError, ValueError):
                                pass
                        accumulated_tokens += artifacts.token_count or 0
                        prior = {"dir": archived, "status": "failed", "req_cov": req_cov}
                        env_id2 = runner.provision(stack, task)
                        try:
                            _seed_repair_workspace(
                                runner.work_dir / env_id2, prior,
                                config_dir / "REQUIREMENTS.json",
                            )
                            a2 = runner.execute(env_id2, stack, task)
                            if not a2.usage_limited:
                                s2 = collector.collect(a2, stack)
                                tf2 = _tests_did_not_run(s2)
                                arch2 = _archive_run_workspace(
                                    archive_root, run_config, rep, a2,
                                    visibility=workspace_config.experiment.visibility,
                                    # the second-chance attempt supersedes attempt 1's
                                    # rep<N> archive — replace it so the archive holds
                                    # the workspace whose scores we record (#42).
                                    replace_existing=True,
                                )
                                if arch2 is not None:
                                    try:
                                        (arch2 / "scores.json").write_text(json.dumps(s2.to_dict()))
                                    except OSError:
                                        pass
                                sf2 = False
                                rc2 = None
                                if (workspace_config.evaluation.enabled and a2.succeeded
                                        and not tf2 and arch2 is not None):
                                    try:
                                        v2, rc2 = _spec_conformance_passes(
                                            arch2, workspace_config.evaluation,
                                            workspace_config.experiment.visibility,
                                            local_agents=workspace_config.playpen.local_agents)
                                        sf2 = v2 is False
                                    except Exception as exc:
                                        click.echo(f"  (2nd-chance gate crashed: {exc})", err=True)
                                # adopt the second attempt as the recorded result
                                artifacts, scores = a2, s2
                                tests_failed, spec_failed, req_cov, archived = tf2, sf2, rc2, arch2
                                # Reassign factual_failed too — it is stored, and
                                # leaving attempt 1's value here would record the
                                # retry under the first attempt's verdict.
                                factual_failed = _factual_gate_failed(s2)
                                run_ok = (a2.succeeded and not tf2 and not sf2
                                          and not factual_failed)
                                run_crashed = not a2.succeeded
                                second_try = True
                        finally:
                            runner.teardown(env_id2)

                    status = ("ok*" if (run_ok and second_try) else "ok" if run_ok
                              else "CRASH" if run_crashed else "FAIL")
                    score_str = ", ".join(
                        f"{k}={v:.2f}" for k, v in scores.to_dict().items()
                    )
                    token_str = ""
                    if artifacts.token_count > 0:
                        cost = artifacts.metadata.get("total_cost_usd", "0")
                        token_str = f" tokens={artifacts.token_count:,} cost=${float(cost):.4f}"
                    click.echo(f" — {status} ({artifacts.duration_seconds:.1f}s) [{score_str}]{token_str}")
                    if not artifacts.succeeded and artifacts.stderr:
                        click.echo(f"    error: {artifacts.stderr[:200]}", err=True)
                    elif tests_failed and artifacts.succeeded:
                        click.echo("    gate: tests did not run (test_coverage=0) — marked failed", err=True)
                    elif spec_failed:
                        click.echo(f"    gate: spec not met (requirement_coverage={req_cov} on two evals) — marked failed", err=True)
                    elif factual_failed:
                        click.echo("    gate: answers wrong (factual_accuracy<1.0) — marked failed", err=True)

                    # Store results
                    _store_run_result(
                        session, run_config, phase, run_idx, rep,
                        artifacts, scores,
                        design_row_id=run_config_to_row_id.get(config_key),
                        # factual_failed MUST be here. It drives `run_ok`, which
                        # sets the console verdict and the rep<N>-failed archive
                        # name — but the DB status comes from THIS argument, and
                        # omitting it recorded a failing run as `completed`. The
                        # monitor and every downstream query read the DB, so the
                        # gate fired everywhere except the place that counts.
                        conformance_reason=(
                            "tests did not run (test_coverage=0)" if tests_failed
                            else f"spec not met (requirement_coverage={req_cov})"
                            if spec_failed
                            else "answers wrong (factual_accuracy<1.0)"
                            if factual_failed else None
                        ),
                        conformance_failed=(tests_failed or spec_failed
                                            or factual_failed),
                        requirement_coverage=req_cov,
                        # a --repair-from cell is itself a repair (2nd attempt),
                        # so it too counts at half credit.
                        second_try=(second_try or repair_from is not None),
                    )
                    # Commit per-run so an interrupt loses at most one run.
                    session.commit()

                    if workspace_config.mlflow is not None:
                        from retort.mlflow_sink import log_run_to_mlflow
                        try:
                            log_run_to_mlflow(
                                workspace_config.mlflow,
                                workspace_config.experiment.name or "retort",
                                run_config, phase, run_idx, rep,
                                artifacts, scores,
                            )
                        except Exception as exc:
                            click.echo(f"  (mlflow log failed: {exc}; continuing)", err=True)

                    if run_ok:
                        completed += 1
                    elif run_crashed:
                        crashed += 1
                    else:
                        failed += 1

                    if artifacts.metadata:
                        try:
                            accumulated_cost += float(artifacts.metadata.get("total_cost_usd") or 0)
                        except (TypeError, ValueError):
                            pass
                    accumulated_tokens += artifacts.token_count or 0
                    if cost_limit is not None and accumulated_cost > cost_limit:
                        raise click.ClickException(
                            f"cost_limit_usd ${cost_limit:.2f} exceeded "
                            f"(accumulated ${accumulated_cost:.4f}) — aborting"
                        )
                    if token_limit is not None and accumulated_tokens > token_limit:
                        raise click.ClickException(
                            f"token_limit {token_limit:,} exceeded "
                            f"(accumulated {accumulated_tokens:,} tokens) — aborting"
                        )
                finally:
                    runner.teardown(env_id)
    except _UsageLimitStop:
        # Graceful stop: commit what finished, leave the limited + remaining
        # cells unrecorded. A plain `--resume` picks them up — no --retry-failed
        # needed, and no usage-limit casualty is mis-scored as a model failure.
        session.commit()
        click.echo(
            "\n⚠ Usage/rate limit reached — stopped cleanly. Completed cells are "
            "saved; the interrupted cell was NOT recorded. Resume with --resume "
            "once your limit resets.",
            err=True,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    summary = f"\nDone: {completed} completed, {failed} failed out of {total_runs}"
    if crashed:
        summary += f" ({crashed} crashed — retried on --resume)"
    if skipped:
        summary += f" ({skipped} skipped via resume)"
    click.echo(summary)


def _parse_shard(spec: str | None) -> tuple[int, int]:
    """Parse '--shard INDEX/TOTAL' into (index, total). None ⇒ (0, 1)."""
    if not spec:
        return (0, 1)
    if "/" not in spec:
        raise click.ClickException(
            f"--shard must be 'INDEX/TOTAL', got {spec!r} (e.g. '0/4')"
        )
    idx_str, _, total_str = spec.partition("/")
    try:
        idx = int(idx_str)
        total = int(total_str)
    except ValueError as exc:
        raise click.ClickException(f"--shard parts must be integers: {exc}") from None
    if total < 1:
        raise click.ClickException("--shard TOTAL must be ≥ 1")
    if idx < 0 or idx >= total:
        raise click.ClickException(f"--shard INDEX must be in [0, {total - 1}], got {idx}")
    return (idx, total)


def _estimate_run_timeout(session, run_config: dict, fallback_minutes: int) -> int:
    """Estimate a per-run timeout from historical _duration_seconds in the DB.

    Looks at completed runs with the same factor config first; if none exist,
    falls back to completed runs sharing the same language (the dominant cost
    driver). The adaptive estimate ``ceil(max_observed * 1.5 / 60)`` only ever
    *extends* the configured budget: the result is clamped to
    ``[fallback_minutes, fallback_minutes * 3]``. It never returns less than the
    configured ``timeout_minutes`` — otherwise an early run (before any slow
    run exists to raise the ceiling) could be killed below the user's budget,
    producing a false all-zeros timeout. Returns ``fallback_minutes`` when no
    history is available.
    """
    import math

    from retort.storage.models import ExperimentRun, RunResult, RunStatus

    config_json = json.dumps(run_config, sort_keys=True)

    all_completed = (
        session.query(ExperimentRun.run_config_json, RunResult.value)
        .join(RunResult, RunResult.run_id == ExperimentRun.id)
        .filter(
            ExperimentRun.status == RunStatus.completed,
            RunResult.metric_name == "_duration_seconds",
        )
        .all()
    )

    exact = [v for cfg, v in all_completed if cfg == config_json]
    if exact:
        durations = exact
    else:
        language = run_config.get("language", "")
        durations = [
            v for cfg, v in all_completed
            if language and json.loads(cfg).get("language") == language
        ]

    if not durations:
        return fallback_minutes

    estimated = math.ceil(max(durations) * 1.5 / 60)
    # Adaptive timeout only extends: never below the configured budget, never
    # above 3x it. Clamping the lower bound to fallback_minutes (rather than 5)
    # prevents early, history-poor runs from being killed under budget.
    return max(fallback_minutes, min(estimated, fallback_minutes * 3))


def _shard_owns(config_key: str, rep: int, shard_index: int, shard_total: int) -> bool:
    """Deterministic per-(cell, replicate) sharding.

    A simple modulo over a hash of the (config, replicate) string. Stable
    across runs and across processes — every shard sees the same partition
    so two polecats with --shard 0/4 and --shard 1/4 never both pick the
    same cell.
    """
    if shard_total <= 1:
        return True
    import hashlib
    digest = hashlib.sha1(f"{config_key}#{rep}".encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % shard_total
    return bucket == shard_index


class _UsageLimitStop(Exception):
    """Raised mid-run when the agent hit a usage/rate limit, to stop the run
    cleanly without recording the interrupted (or remaining) cells as failures."""


@main.group()
def report() -> None:
    """Analysis and reporting commands."""


@main.group()
def plugin() -> None:
    """Plugin management commands."""


@main.group()
def export() -> None:
    """Export experiment data for downstream analysis."""


@main.group()
def tasks() -> None:
    """Task registry commands (the task sources retort can run)."""


if __name__ == "__main__":
    main()


# --- extracted command modules (import LAST: main + all helpers are defined above) ---
from retort.commands import scoring  # noqa: E402,F401
from retort.commands import reporting  # noqa: E402,F401
from retort.commands import utility  # noqa: E402,F401
from retort.commands import workspace  # noqa: E402,F401
from retort.commands import analysis  # noqa: E402,F401
from retort.commands import monitoring  # noqa: E402,F401
from retort.commands import rebuild  # noqa: E402,F401
from retort.commands.scoring import (  # noqa: E402,F401  backward-compat re-exports
    evaluate, reevaluate, rescore, diagnose, recover, _nonpassing_languages,
)
