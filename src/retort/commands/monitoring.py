"""The live run monitor command."""
from __future__ import annotations

import click  # noqa: F401

from retort import cli
from retort.cli import main


@main.command("monitor")
@click.argument("target", required=False)
@click.option(
    "--db",
    type=click.Path(exists=True),
    default=None,
    help="Path to the retort SQLite database (inferred from TARGET if omitted).",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Workspace YAML; read to derive the expected total from replicates "
    "(inferred from TARGET if omitted).",
)
@click.option(
    "--total",
    type=int,
    default=None,
    help="Override the expected total run count (design cells × replicates).",
)
@click.option(
    "--watch/--once",
    default=False,
    help="Refresh continuously until all runs finish (Ctrl-C to stop).",
)
@click.option(
    "--interval",
    type=float,
    default=10.0,
    show_default=True,
    help="Seconds between refreshes in --watch mode.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit a JSON snapshot instead of the text report.",
)
def monitor_cmd(
    target: str | None,
    db: str | None,
    config: str | None,
    total: int | None,
    watch: bool,
    interval: float,
    as_json: bool,
) -> None:
    """Show live progress of an experiment run database.

    TARGET is an experiment directory (or a .db path): `retort monitor
    experiment-5` resolves to experiment-5/retort.db and its workspace.yaml.
    --db / --config override the inferred paths.

    With NO argument it watches the experiment in flight: the most recently
    written experiment database is picked automatically, so plain `retort monitor`
    (optionally `--watch`) is all you need while a run is going.

    Summarizes completed/remaining runs, per-cell coverage, cost and token
    totals, throughput, and an ETA. Safe to point at a database that one or
    more ``retort run`` shards are actively writing. Failed runs are reported
    as pending (they re-run under --resume --retry-failed), so a resume run
    isn't mistaken for "almost done". With --watch it refreshes until the run
    finishes. Progress is completed/(design-cells × replicates); pass --config
    (to read replicates) or --total when neither can be inferred.
    """
    import time

    from retort.reporting.monitor import (
        build_snapshot,
        render_json,
        render_text,
        resolve_target,
    )
    from retort.storage.database import get_engine, get_session_factory

    try:
        db_path, config_path = resolve_target(target, db, config)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if not db_path.is_file():
        raise click.ClickException(f"Database not found: {db_path}")

    replicates: int | None = None
    if config_path is not None:
        from retort.config.loader import load_workspace

        try:
            replicates = load_workspace(str(config_path)).playpen.replicates
        except Exception as exc:  # noqa: BLE001 - surfaced as a warning, non-fatal
            click.echo(
                f"warning: could not read replicates from {config_path}: {exc}",
                err=True,
            )

    engine = get_engine(db_path)
    session_factory = get_session_factory(engine)

    def _snapshot():
        session = session_factory()
        try:
            return build_snapshot(session, replicates=replicates, expected_total=total)
        finally:
            session.close()

    try:
        while True:
            snap = _snapshot()
            active = cli._discover_active_runs(db_path)
            if watch and not as_json:
                click.echo("\033[2J\033[H", nl=False)  # clear screen + cursor home
            if as_json:
                out = render_json(snap, active=active)
            else:
                out = render_text(snap, db_path=str(db_path), active=active)
            click.echo(out)
            if not watch:
                break
            # Watch until the RUN PROCESS finishes, not until `snap.is_done`. is_done
            # counts a failed cell as terminal, so it goes True mid-run during a
            # --retry-failed pass (and any run whose DB already looks fully measured),
            # which made --watch exit early. The `retort run` process is alive for the
            # whole experiment, so its absence is the correct stop signal: a live run
            # keeps the loop going; a finished/abandoned DB renders once and exits.
            if not cli._run_in_flight(db_path):
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("", err=True)
    finally:
        engine.dispose()
