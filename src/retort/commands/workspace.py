"""Workspace + lifecycle commands (init, visibility-check, design generate, promote, intake)."""
from __future__ import annotations

import click  # noqa: F401

from retort import cli
from retort.cli import main, design


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite existing directory")
@click.option(
    "--visibility",
    type=click.Choice(["public", "private"]),
    default="private",
    show_default=True,
    help="public = artifacts safe to publish; private = local-only (fail-closed default).",
)
def init(name: str, force: bool, visibility: str):
    """Initialize a new Retort workspace.

    Creates a workspace directory with a config template, a visibility-aware
    .gitignore, and an initialized SQLite database.
    """
    workspace = cli.Path(name).resolve()

    if workspace.exists() and not force:
        raise click.ClickException(
            f"Directory {name!r} already exists. Use --force to overwrite."
        )

    if workspace.exists() and force:
        cli.shutil.rmtree(workspace)

    workspace.mkdir(parents=True, exist_ok=True)

    # Write config template
    config_path = workspace / "workspace.yaml"
    config_path.write_text(
        cli.WORKSPACE_TEMPLATE.replace("__NAME__", name).replace("__VISIBILITY__", visibility)
    )

    # Write visibility-aware .gitignore
    gitignore_path = workspace / ".gitignore"
    gitignore_path.write_text(cli._gitignore_for(visibility))

    # Initialize database
    db_path = workspace / "retort.db"
    cli._init_database(db_path)

    click.echo(f"Initialized Retort workspace in {workspace}")
    click.echo(f"  Config:     {config_path}")
    click.echo(f"  Gitignore:  {gitignore_path} (visibility={visibility})")
    click.echo(f"  Database:   {db_path}")
    if visibility == "private":
        click.echo("  Visibility: PRIVATE — runs/, reports/, evaluations stay local.")
    else:
        click.echo("  Visibility: PUBLIC — runs/ and reports/web/ are git-tracked.")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")
    click.echo("  # Edit workspace.yaml to define your factors and responses")
    click.echo("  retort design generate --phase screening")


@main.command("visibility-check")
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="cli.Path to workspace YAML config.",
)
def visibility_check(config: str) -> None:
    """Audit which workspace artifacts would be published vs kept local.

    Reads ``experiment.visibility`` from the workspace config, then walks
    the workspace directory and reports each notable artifact as PUBLISHED
    or LOCAL based on .gitignore rules. Exits non-zero if a private-mode
    workspace would publish a sensitive path.
    """
    from retort.config.loader import load_workspace

    cfg = load_workspace(config)
    workspace_dir = cli.Path(config).resolve().parent
    visibility = cfg.experiment.visibility

    click.echo(f"Workspace:  {workspace_dir}")
    click.echo(f"Visibility: {visibility}")
    click.echo()

    gitignore_path = workspace_dir / ".gitignore"
    ignored_lines: set[str] = set()
    if gitignore_path.is_file():
        for line in gitignore_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ignored_lines.add(line.rstrip("/"))

    leaks: list[str] = []
    for entry in sorted(workspace_dir.iterdir()):
        name = entry.name
        if name in {".git", ".gitignore", "workspace.yaml"}:
            continue
        ignored = name in ignored_lines or f"{name}/" in ignored_lines or name.rstrip("/") in ignored_lines
        status = "LOCAL " if ignored else "PUBLISH"
        click.echo(f"  {status}  {name}")
        if visibility == "private" and not ignored and name in cli._PRIVATE_SENSITIVE_PATHS:
            leaks.append(name)

    if leaks:
        click.echo()
        click.echo(
            f"ERROR: visibility=private but these sensitive paths are NOT gitignored: {leaks}",
            err=True,
        )
        click.echo("Add them to .gitignore before committing.", err=True)
        raise click.ClickException("private workspace would leak sensitive artifacts")


@design.command("generate")
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    required=True,
    help="Experiment phase (screening = Resolution III, characterization = Resolution IV).",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to workspace YAML config. If omitted, reads factors from stdin as JSON.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output CSV path. Defaults to stdout.",
)
def design_generate(phase: str, config: str | None, output: str | None) -> None:
    """Generate a fractional factorial design matrix.

    Reads factor definitions and produces a design matrix for the given phase.
    Without --config, reads a JSON dict of {factor_name: [levels]} from stdin.
    When workspace.yaml contains ``design.fraction``, the generated matrix is
    automatically reduced to that fraction of the full factorial.
    """
    import math

    registry = cli._load_factors(config)

    if len(registry) < 2:
        click.echo("Error: need at least 2 factors for design generation.", err=True)
        cli.sys.exit(1)

    # Honour design.fraction from workspace config when available
    fraction: float | None = None
    if config is not None:
        from retort.config.loader import load_workspace
        ws = load_workspace(config)
        fraction = ws.design.fraction

    result = cli.generate_design(registry, phase, fraction=fraction)

    full_n = result.full_factorial_size or math.prod(f.num_levels for f in registry.factors)
    frac_label = f"{result.num_runs}/{full_n}" if result.num_runs != full_n else f"{full_n} (full factorial)"

    if output:
        result.to_csv(output)
        click.echo(f"Design matrix written to {output} ({result.num_runs} runs, {frac_label})")
    else:
        # Summary to stderr so it doesn't pollute a piped CSV
        click.echo(f"# {result.num_runs} runs — {frac_label}", err=True)
        click.echo(result.matrix.to_csv(index_label="run"))


@main.command()
@click.argument("stack_id")
@click.option(
    "--from",
    "from_phase",
    type=click.Choice(["screening", "trial", "production"]),
    required=True,
    help="Current lifecycle phase of the stack.",
)
@click.option(
    "--to",
    "to_phase",
    type=click.Choice(["trial", "production", "retired"]),
    required=True,
    help="Target lifecycle phase.",
)
@click.option(
    "--evidence",
    type=str,
    default=None,
    help='JSON object of evidence metrics, e.g. \'{"p_value": 0.05}\'.',
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to workspace YAML config for gate thresholds.",
)
def promote(
    stack_id: str,
    from_phase: str,
    to_phase: str,
    evidence: str | None,
    config_path: str | None,
) -> None:
    """Evaluate a promotion gate and report whether a stack passes.

    Example::

        retort promote my-stack --from screening --to trial \\
            --evidence '{"p_value": 0.05}' --config workspace.yaml
    """
    from retort.config.schema import PromotionConfig
    from retort.promotion.gates import evaluate_gate

    # Determine the gate name from the transition.
    gate_name = f"{from_phase}_to_{to_phase}"
    valid_gates = {"screening_to_trial", "trial_to_production", "production_to_retired"}
    if gate_name not in valid_gates:
        raise click.ClickException(
            f"Invalid transition: {from_phase} → {to_phase}. "
            f"Valid transitions: screening→trial, trial→production, production→retired."
        )

    # Parse evidence.
    if evidence is None:
        evidence_dict: dict[str, float] = {}
    else:
        try:
            evidence_dict = cli.json.loads(evidence)
        except cli.json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --evidence: {exc}") from exc

    # Load promotion config from workspace YAML or use defaults.
    if config_path is not None:
        try:
            import yaml
        except ImportError:
            raise click.ClickException(
                "pyyaml required for --config. Install with: pip install pyyaml"
            )
        with open(config_path) as f:
            data = yaml.safe_load(f)
        promo_data = data.get("promotion", {})
        promo_config = PromotionConfig(**promo_data)
    else:
        promo_config = PromotionConfig()

    result = evaluate_gate(gate_name, evidence_dict, promo_config)

    if result.passed:
        click.echo(f"PASS: {stack_id} may advance {from_phase} → {to_phase}")
    else:
        click.echo(f"FAIL: {stack_id} does not pass {from_phase} → {to_phase}")
    click.echo(f"  {result.detail}")


@main.command()
@click.option(
    "--factor",
    type=str,
    required=True,
    help="Name of the factor gaining a new level (e.g., 'agent').",
)
@click.option(
    "--level",
    type=str,
    required=True,
    help="New level value to add (e.g., 'new-agent-v1').",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config.",
)
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    default="screening",
    show_default=True,
    help="Design phase for augmentation.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write augmentation rows to CSV file.",
)
@click.option(
    "--nrestarts",
    type=int,
    default=40,
    show_default=True,
    help="Number of optimizer restarts for D-optimal generation.",
)
def intake(
    factor: str,
    level: str,
    config_path: str,
    phase: str,
    output: str | None,
    nrestarts: int,
) -> None:
    """Ingest a new candidate (factor level) and generate augmentation runs.

    When a new candidate appears (e.g., a new AI agent ships), this command
    triggers D-optimal augmentation to extend the existing design matrix
    with the minimum new runs needed.

    Example::

        retort intake --factor agent --level "new-agent-v1"
    """
    from retort.scheduler.intake import intake_candidate, load_existing_design

    registry, existing_design = load_existing_design(config_path, phase)

    try:
        result = intake_candidate(
            factor_name=factor,
            new_level=level,
            registry=registry,
            existing_design=existing_design,
            nrestarts=nrestarts,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
    except ImportError as exc:
        raise click.ClickException(str(exc)) from None

    click.echo(f"Intake: {factor}={level}")
    click.echo(f"  Stack ID:     {result.stack_id}")
    click.echo(f"  Lifecycle:    {result.lifecycle_state}")
    click.echo(f"  D-efficiency: {result.augmentation.d_efficiency:.6f}")
    click.echo(f"  New runs:     {result.num_new_runs}")
    click.echo(f"  Total design: {result.augmentation.full_design.num_runs} runs")

    if result.num_new_runs > 0:
        click.echo(f"\nAugmentation rows:")
        click.echo(result.new_rows.to_string(index=False))

    if output:
        result.new_rows.to_csv(output, index=False)
        click.echo(f"\nAugmentation rows written to {output}")
