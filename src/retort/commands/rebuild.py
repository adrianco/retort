"""`retort rebuild` / `retort report runtime` — make archived runs runnable again,
then measure how fast the produced programs actually are.

WHY THIS EXISTS. An archived run is deliberately NOT runnable: `_ARCHIVE_NOISE`
strips `dist/`, `build/`, `target/`, `node_modules/` and friends so the repo does
not carry a compiled artifact per cell (a Go binary alone is ~15 MB). That is the
right call for storage and the wrong state for measurement — you cannot time a
program whose interpreter entrypoint was thrown away. `rebuild` restores and
rebuilds each archived run from the source and lockfiles that WERE kept, so a
past experiment can be measured long after it finished.

WHAT IT DOES NOT CLAIM. A rebuilt tree is reproducible, not identical. The
lockfiles are archived (`package-lock.json`, `Cargo.lock`, `rebar.lock`, …) so
dependency versions pin, but the TOOLCHAIN is whatever is installed today —
rebuilding a six-month-old run under a newer compiler measures today's compiler.
Every rebuild records the toolchain versions it used for exactly that reason.
"""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import click

from retort.cli import main, report
from retort.scoring.scorers import runtime as rt

#: Commands whose output identifies the toolchain a rebuild actually used.
_TOOLCHAIN_PROBES = {
    "typescript": ["node", "--version"],
    "rust": ["cargo", "--version"],
    "go": ["go", "version"],
    "java": ["mvn", "--version"],
    "csharp": ["dotnet", "--version"],
    "elixir": ["elixir", "--version"],
    "erlang": ["erl", "-eval", "erlang:display(erlang:system_info(otp_release)), halt().",
               "-noshell"],
    "clojure": ["clojure", "--version"],
    "swift": ["swift", "--version"],
    "python": ["python3", "--version"],
}


def _toolchain(language: str) -> str:
    cmd = _TOOLCHAIN_PROBES.get(language)
    if not cmd:
        return ""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().split("\n")[0][:80]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "(not installed)"


def _archived_runs(experiment_dir: Path) -> list[Path]:
    """Every archived run, excluding superseded `-failed` snapshots.

    A `rep1-failed` directory is the wreckage of an attempt that was re-run;
    rebuilding it would double-count the language and time code that never
    passed a gate.
    """
    return sorted(p for p in (experiment_dir / "runs").glob("*/rep*")
                  if p.is_dir() and not p.name.endswith("-failed"))


def _language_of(run_dir: Path) -> str:
    for part in run_dir.parent.name.split("_"):
        if part.startswith("language="):
            return part.split("=", 1)[1]
    return ""


@main.command("rebuild")
@click.option("--experiment-dir", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Experiment dir whose runs/ archives should be made runnable.")
@click.option("--languages", default="", help="Comma-separated filter (default: all).")
@click.option("--json", "json_out", type=click.Path(path_type=Path),
              help="Write the per-run rebuild status here.")
def rebuild_cmd(experiment_dir: Path, languages: str, json_out: Path | None) -> None:
    """Restore deps and rebuild archived runs so they can be run and measured.

    Archives keep source + lockfiles but not build output, so this is what turns
    a stored experiment back into something executable.
    """
    wanted = {s.strip() for s in languages.split(",") if s.strip()}
    runs = _archived_runs(experiment_dir)
    if not runs:
        raise click.ClickException(f"no archived runs under {experiment_dir}/runs")

    results = []
    for run_dir in runs:
        lang = _language_of(run_dir)
        if wanted and lang not in wanted:
            continue
        cmd, why = rt._build_then_entry(run_dir, lang)
        ok = cmd is not None
        results.append({
            "run": str(run_dir), "language": lang, "runnable": ok,
            "entry": cmd, "note": why, "toolchain": _toolchain(lang),
        })
        click.echo(f"  {lang:11s} {'runnable' if ok else 'NOT runnable: ' + why}")

    n_ok = sum(1 for r in results if r["runnable"])
    click.echo(f"\n{n_ok}/{len(results)} archived runs are now runnable.")
    click.echo(f"host: {platform.platform()}")
    click.echo("NOTE: dependency versions pin via the archived lockfiles, but the "
               "TOOLCHAIN is whatever is installed today — the versions used are "
               "recorded per run.")
    if json_out:
        json_out.write_text(json.dumps(results, indent=1))
        click.echo(f"→ {json_out}")


@report.command("runtime")
@click.option("--experiment-dir", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--task", default="", help="Override task detection.")
@click.option("--languages", default="", help="Comma-separated filter (default: all).")
@click.option("--json", "json_out", type=click.Path(path_type=Path))
def runtime_report_cmd(experiment_dir: Path, task: str, languages: str,
                       json_out: Path | None) -> None:
    """Measure produced-program runtime across an experiment's archived runs.

    Rebuilds as needed (same path as `retort rebuild`), then times a FIXED probe
    — the same request against every implementation, not the model's own test
    suite, whose duration mostly reflects how many tests it chose to write.
    """
    if rt._machine_is_busy():
        raise click.ClickException(
            "an experiment is running — wall-clock timing would be invalid. Wait.")

    wanted = {s.strip() for s in languages.split(",") if s.strip()}
    rows = []
    for run_dir in _archived_runs(experiment_dir):
        lang = _language_of(run_dir)
        if wanted and lang not in wanted:
            continue
        t = task or rt.detect_task(run_dir)
        res = rt.measure(run_dir, t, lang, allow_busy=True)
        rows.append(res)
        click.echo(f"  {lang:11s} {'ok' if res.ok else 'NO RESULT: ' + res.note}",
                   err=True)

    ok = [r for r in rows if r.ok]
    click.echo(f"\n| language | cold start | steady median | min | max | n |")
    click.echo("|---|---:|---:|---:|---:|---:|")
    for r in sorted(ok, key=lambda x: x.steady_median_ms or 9e9):
        click.echo(f"| {r.language} | {r.cold_start_ms:.0f} ms | "
                   f"**{r.steady_median_ms:.0f} ms** | {r.steady_min_ms:.0f} | "
                   f"{r.steady_max_ms:.0f} | {r.iters} |")
    for r in rows:
        if not r.ok:
            click.echo(f"| {r.language} | — | *{r.note}* | | | |")
    if len(ok) > 1:
        f = min(ok, key=lambda x: x.steady_median_ms)
        s = max(ok, key=lambda x: x.steady_median_ms)
        click.echo(f"\nSpread: **{s.steady_median_ms / f.steady_median_ms:.1f}x** "
                   f"({f.language} → {s.language}), {len(ok)}/{len(rows)} measured.")
    if json_out:
        json_out.write_text(json.dumps([r.as_dict() for r in rows], indent=1))
