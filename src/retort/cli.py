"""Retort CLI entry point."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from retort import __version__

WORKSPACE_TEMPLATE = """\
# Retort workspace configuration
# See docs/configuration.md for full reference

factors:
  language:
    levels: [python, typescript, go]
  agent:
    levels: [claude-code, cursor, copilot]
  framework:
    levels: [fastapi, nextjs, stdlib]

responses:
  - code_quality
  - token_efficiency
  - build_time
  - test_coverage

playpen:
  runner: docker
  replicates: 3
  timeout_minutes: 30

design:
  screening_resolution: 3
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }
"""


@click.group()
@click.version_option(version=__version__, prog_name="retort")
def main() -> None:
    """Retort — Platform Evolution Engine.

    Distill the best from the combinatorial mess.
    """


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite existing directory")
def init(name: str, force: bool):
    """Initialize a new Retort workspace.

    Creates a workspace directory with a config template and initialized SQLite database.
    """
    workspace = Path(name).resolve()

    if workspace.exists() and not force:
        raise click.ClickException(
            f"Directory {name!r} already exists. Use --force to overwrite."
        )

    if workspace.exists() and force:
        shutil.rmtree(workspace)

    workspace.mkdir(parents=True, exist_ok=True)

    # Write config template
    config_path = workspace / "workspace.yaml"
    config_path.write_text(WORKSPACE_TEMPLATE)

    # Initialize database
    db_path = workspace / "retort.db"
    _init_database(db_path)

    click.echo(f"Initialized Retort workspace in {workspace}")
    click.echo(f"  Config:   {config_path}")
    click.echo(f"  Database: {db_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")
    click.echo("  # Edit workspace.yaml to define your factors and responses")
    click.echo("  retort design generate --phase screening")


def _init_database(db_path: Path) -> None:
    """Create and initialize the SQLite database with all tables."""
    from retort.storage.database import create_tables, get_engine

    engine = get_engine(db_path)
    create_tables(engine)
    engine.dispose()


if __name__ == "__main__":
    main()
