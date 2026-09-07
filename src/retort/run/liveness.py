"""Liveness of a running experiment, read from the process table.

Extracted from cli.py (the first cut of its split -- see docs). Everything
here answers one question for `retort monitor`: is a `retort run` still
alive for this experiment, and if so how far into its context window is the
agent? None of it touches the database schema or the run pipeline, and none
of it is used by `run_experiments` itself -- its only production consumer is
`monitor_cmd`, which is why it was the safe place to start.

`cli.py` re-exports every name below, so `cli._discover_active_runs` and
`from retort.cli import _etime_to_seconds` keep working unchanged.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

def _etime_to_seconds(etime: str) -> float | None:
    """Parse BSD/GNU ps etime ([[dd-]hh:]mm:ss) into seconds."""
    etime = etime.strip()
    if not etime:
        return None
    days = 0
    if "-" in etime:
        d, etime = etime.split("-", 1)
        if not d.isdigit():
            return None
        days = int(d)
    parts = etime.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    secs = 0
    for n in nums:
        secs = secs * 60 + n
    return float(days * 86400 + secs)

def _retort_run_pids_for(db_path: Path) -> list[str]:
    """PIDs of the ``retort run`` process(es) working on THIS experiment.

    Matches two invocation styles, because the earlier argv-only matching missed
    the one the docs actually recommend:

    * ``cd <exp> && retort run --config workspace.yaml`` — the experiment is named
      NOWHERE in argv (paths are relative), so we match on the process **working
      directory** being the experiment dir. This is the common case that made
      ``--watch`` exit immediately and hid the running cell.
    * ``retort run <exp>`` / ``--config <exp>/workspace.yaml`` — the slug or
      dir-name DOES appear in argv, so we match that too (cwd may be elsewhere).

    Best-effort and local-only: returns [] if it can't tell (no process access).
    """
    import subprocess

    exp_dir = db_path.resolve().parent
    slug = next((p for p in reversed(exp_dir.parts) if p.startswith("experiment-")), None)

    def _run(args: list[str]) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=5)
        except Exception:  # noqa: BLE001 — best-effort; never break the monitor
            return None

    # Candidate processes: every `retort run` carries the (required) `--phase`
    # flag. The `[-]` char class stops pgrep from reading the pattern as a flag
    # and stops the pattern from matching pgrep's own argv.
    r = _run(["pgrep", "-f", r"[-]-phase"])
    if r is None or r.returncode not in (0, 1):
        return []

    matched: list[str] = []
    for pid in r.stdout.split():
        psc = _run(["ps", "-o", "command=", "-p", pid])
        cmd = psc.stdout.strip() if psc else ""
        if " run " not in f" {cmd} ":  # must be the `run` subcommand, not design/report
            continue
        # (a) argv names the experiment (the `retort run <exp>` style).
        if (slug and slug in cmd) or f"/{exp_dir.name}" in cmd or f" {exp_dir.name}" in cmd:
            matched.append(pid)
            continue
        # (b) the process cwd IS the experiment dir (the `cd <exp> && retort run
        #     --config workspace.yaml` style — nothing identifying in argv).
        lf = _run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"])
        cwd = ""
        if lf is not None:
            for line in lf.stdout.splitlines():
                if line.startswith("n"):
                    cwd = line[1:]
                    break
        try:
            if cwd and Path(cwd).resolve() == exp_dir:
                matched.append(pid)
        except OSError:
            pass
    return matched

def _live_context_tokens(
    workspace: Path, serving_log: Path | None, elapsed_s: float | None = None
) -> tuple[int | None, int | None]:
    """Context the in-flight run is CURRENTLY carrying, for the live monitor.

    Two sources, because agents differ in what they expose while running:

    * the agent's own stream (``_agent_stdout.log``) — Claude's ``stream-json``
      and omp's ``message_end`` both report each turn's usage as it happens;
    * the **serving log**, for agents that stream nothing to stdout while working
      (Hermes emits essentially no stdout until it exits, so its context would be
      invisible otherwise).

    Takes the LAST reading, not the max — this is "what is it carrying right now",
    which is what tells you a run is ballooning toward non-termination while you
    can still act on it.
    """
    import datetime as _dt
    import json as _json

    # Shared with the local runner: context = prompt + both cache reads (NOT the
    # output). Imported here because this path (live context for an in-flight
    # cell) was unreachable until the run-process detection was fixed to match by
    # cwd, so the missing import never fired.
    from retort.playpen.local_runner import _turn_context

    log = workspace / "_agent_stdout.log"
    if log.is_file():
        try:
            tail = log.read_bytes()[-400_000:].decode("utf-8", "replace")
        except OSError:
            tail = ""
        latest: int | None = None
        peak = 0
        for line in tail.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = _json.loads(line)
            except ValueError:
                continue
            u = (ev.get("message") or {}).get("usage") or {}
            if not u:
                continue
            if ev.get("type") == "assistant":  # claude stream-json
                latest = _turn_context(u)
            elif ev.get("type") == "message_end":  # omp
                latest = (
                    int(u.get("input", 0) or 0)
                    + int(u.get("cacheRead", 0) or 0)
                    + int(u.get("cacheWrite", 0) or 0)
                )
            else:
                continue
            peak = max(peak, latest)
        if latest:
            return latest, peak

    if serving_log and serving_log.is_file():
        try:
            with open(serving_log, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 400_000))
                tail = f.read().decode("utf-8", "replace")
        except OSError:
            return None, None
        # The serving log is SHARED by every run, so a naive max over the tail
        # reports the PREVIOUS cell's peak — a run 1 minute old was showing
        # "pk 114K" inherited from the rust cell before it. Restrict to lines
        # timestamped within this run's own window.
        since = None
        if elapsed_s:
            since = _dt.datetime.now() - _dt.timedelta(seconds=elapsed_s + 30)
        hits: list[int] = []
        for line in tail.splitlines():
            m = re.search(r"prompt:\s*(\d+)", line)
            if not m:
                continue
            if since is not None:
                ts = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                if ts:
                    try:
                        when = _dt.datetime.strptime(ts.group(1), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        when = None
                    if when is not None and when < since:
                        continue  # belongs to an earlier run
            hits.append(int(m.group(1)))
        if hits:
            return hits[-1], max(hits)
    return None, None

def _discover_active_runs(db_path: Path) -> list[dict]:
    """Best-effort list of in-flight agent runs for this experiment.

    Finds ``retort run`` processes referencing this experiment directory, then
    their ``claude`` agent children, and reads each child's playpen
    ``stack.json`` (cell) plus ``ps`` elapsed time. Returns [] when it can't
    determine them (no process access / not the run host). Local-only.
    """
    import json as _json
    import os
    import subprocess
    import time

    # Agent CLIs retort shells out to. The active job is one of these — NOT just
    # `claude`: a local-model cell runs `omp`/`hermes`/`gemini`/`opencode`, so
    # keying only on `claude` showed nothing while a local model was working and
    # only lit up during the (claude) spec-gate eval.
    _AGENT_BINS = ("claude", "omp", "hermes", "gemini", "opencode", "codex")

    def _run(args: list[str]) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=5)
        except Exception:  # noqa: BLE001 - best-effort; never fail the monitor
            return None

    # The `retort run` parents for this experiment — matched by cwd OR argv, so a
    # run launched from inside the experiment dir (nothing identifying in argv) is
    # found, not just the `retort run <exp>` style. Returns [] off the run host.
    run_pids = _retort_run_pids_for(db_path)
    if not run_pids:
        return []
    # Launchers that sit BETWEEN `retort run` and the agent, so the agent is a
    # grandchild rather than a direct child (e.g. `uv run … hermes`, an
    # `env`-shebang shim, a direnv/nix wrapper). Descend through these when a
    # direct child is one of them — otherwise a wrapped agent shows nothing in the
    # live monitor even though it is working.
    _WRAPPERS = {"uv", "uvx", "env", "poetry", "pdm", "direnv", "nix"}

    def _agent_candidate_pids(parent: str, depth: int = 0) -> list[str]:
        ch = _run(["pgrep", "-P", parent])
        if ch is None or depth > 4:
            return []
        out: list[str] = []
        for cpid in ch.stdout.split():
            psc = _run(["ps", "-o", "command=", "-p", cpid])
            cmd0 = psc.stdout.strip() if psc else ""
            first = os.path.basename(cmd0.split()[0]) if cmd0 else ""
            if first in _WRAPPERS:
                out.extend(_agent_candidate_pids(cpid, depth + 1))
            else:
                out.append(cpid)
        return out

    active: list[dict] = []
    seen: set[str] = set()
    # A cell being SCORED has no agent child — the runtime and factual probes
    # launch the program the model wrote (`npm start`, a Rust binary, a JVM).
    # The probe leaves a breadcrumb keyed by the `retort run` pid; without it the
    # monitor showed a live run with no recognizable child and reported a working
    # cell as not started.
    from retort.scoring import probe_status as _ps
    for rpid in run_pids:
        crumb = _ps.read(int(rpid)) if str(rpid).isdigit() else None
        if crumb:
            active.append({
                "label": crumb.get("label") or "scoring",
                "replicate": None,
                "elapsed_s": max(0.0, time.time() - float(crumb["updated"])),
                "evaluating": False,
                "phase": crumb.get("phase") or "scoring",
                "context_tokens": None,
                "context_peak": None,
                "second_try": False,
            })
        for cpid in _agent_candidate_pids(rpid):
            psc = _run(["ps", "-o", "command=", "-p", cpid])
            cmd = psc.stdout.strip() if psc else ""
            if not cmd:
                continue
            # Which agent CLI is this child? Check the basename of the first two
            # argv tokens — the binary is either the program itself (`claude`,
            # `omp`, `gemini`) or the script run by an interpreter (a pip/npm
            # entry point like `Python .../bin/hermes` or `node .../opencode`).
            # Scanning only the first two tokens avoids matching an agent name
            # that merely appears inside the prompt text.
            tokens = cmd.split()
            candidates = {os.path.basename(t) for t in tokens[:2]}
            agent_bin = next((b for b in _AGENT_BINS if b in candidates), None)
            if agent_bin is None:
                continue
            # The spec-gate eval is a `claude` child WITHOUT `--max-turns` (the
            # claude-code *agent* always passes --max-turns). Any local-agent CLI
            # child (omp/hermes/…) is the job itself, never the eval.
            evaluating = agent_bin == "claude" and "--max-turns" not in cmd
            lf = _run(["lsof", "-a", "-p", cpid, "-d", "cwd", "-Fn"])
            cwd = ""
            if lf is not None:
                for line in lf.stdout.splitlines():
                    if line.startswith("n"):
                        cwd = line[1:]
                        break
            if not cwd or cwd in seen:
                continue
            seen.add(cwd)
            # Which CELL is this process working on? The agent runs *in* the playpen,
            # so its cwd holds stack.json. The spec-gate EVALUATOR does not — it is a
            # claude process launched elsewhere, carrying the cell only as
            # `run_dir=<archived run dir>` in its prompt. Without this it rendered as
            # a bare "?", which is useless precisely when a long eval is the thing
            # holding the experiment up.
            cell_dir = Path(cwd)
            if not (cell_dir / "stack.json").is_file():
                m = re.search(r"run_dir=(\S+)", cmd)
                if m:
                    # The path is embedded in prose, so it picks up trailing
                    # sentence punctuation — strip it, or stack.json is never found
                    # and the label degrades to the raw archive dir name.
                    cell_dir = Path(m.group(1).rstrip('"\'.,;:)'))
            label = "?"
            try:
                sj = _json.loads((cell_dir / "stack.json").read_text())
                # Prefer the short stack-preset id over the full model id: a cell
                # carrying both (a stack-preset sweep) would otherwise render as
                # `rust/mlxlocal/Qwen3.6-35B-A3B/...`, where the model id's own
                # slashes masquerade as extra factors. Fall back to the model's
                # last path segment when there is no preset.
                fields = ("language", "stack", "agent", "tooling", "prompt")
                if "stack" not in sj:
                    fields = ("language", "model", "agent", "tooling", "prompt")
                label = "/".join(
                    str(sj[k]).rsplit("/", 1)[-1]
                    for k in fields
                    if k in sj and str(sj[k]) not in ("", "unknown")
                )
            except Exception:  # noqa: BLE001
                pass
            if label == "?" and cell_dir != Path(cwd):
                # No stack.json (an archive predating it) — the path still names the
                # cell: .../runs/<cell>/rep2 → "<cell> rep2".
                label = f"{cell_dir.parent.name} {cell_dir.name}"
            et = _run(["ps", "-o", "etime=", "-p", cpid])
            elapsed = _etime_to_seconds(et.stdout) if et else None
            # Serving log (if this experiment drives a local server via stack
            # presets) — the only place a non-streaming agent's context is visible.
            _serving_log = None
            try:
                import yaml as _yaml
                _sp = db_path.parent / "stacks.yaml"
                if _sp.is_file():
                    _lg = ((_yaml.safe_load(_sp.read_text()) or {})
                           .get("serving", {}) or {}).get("log")
                    if _lg:
                        _serving_log = Path(_lg)
            except Exception:  # noqa: BLE001 — the monitor must never break a run
                _serving_log = None
            # Do NOT attribute the served model's context to the EVALUATOR. The
            # judge is a separate cloud model; reading the serving log for it just
            # reports the last local run's context (we were showing a stale
            # "ctx 37K (pk 114K)" against an opus judge that never touched it).
            _ctx_now, _ctx_peak = (
                (None, None) if evaluating
                else _live_context_tokens(Path(cwd), _serving_log, elapsed)
            )
            # Is this the self-repair SECOND CHANCE? A repair playpen is seeded with
            # FEEDBACK.md (the requirement checklist + the prior evaluation verdict);
            # a first attempt never has one. Without this the monitor shows the same
            # cell "evaluating" with a reset clock and it reads as a stuck loop.
            _second = (cell_dir / "FEEDBACK.md").is_file() or (
                Path(cwd) / "FEEDBACK.md"
            ).is_file()
            active.append(
                {
                    "label": label,
                    "replicate": None,
                    "elapsed_s": elapsed,
                    "evaluating": evaluating,
                    "second_try": _second,
                    "context_tokens": _ctx_now,
                    "context_peak": _ctx_peak,
                }
            )
    return active

def _run_in_flight(db_path: Path) -> bool:
    """True if a ``retort run`` process is still working on this experiment.

    The `--watch` loop uses this rather than ``snapshot.is_done`` to decide when
    to stop: a *failed* cell counts as a terminal data point, so `is_done` goes
    True during a ``--resume --retry-failed`` pass (or any run whose DB looks
    fully measured) even while `retort run` is actively re-running cells — which
    made `--watch` exit mid-run. The run process, by contrast, is alive for the
    whole experiment (between cells and during the spec-gate eval too), so it is
    the correct "still going" signal. Best-effort: returns False if it can't tell.
    """
    # Matched by cwd OR argv (see _retort_run_pids_for): a run launched from
    # inside the experiment dir names the experiment nowhere in argv, so the old
    # argv-only pgrep found nothing and `--watch` exited immediately mid-run.
    return bool(_retort_run_pids_for(db_path))
