"""Runtime scorer — how fast the PRODUCED PROGRAM is, per language.

WHY NOT JUST PARSE THE TEST SUITE'S OWN TIMING. Nearly every framework prints a
duration (`ℹ duration_ms 61.3`, `Finished in 0.033 seconds`, `Time Elapsed
00:00:00.36`, …), and scraping those is a morning's work. It would measure the
wrong thing. A suite's wall time is dominated by process start-up, framework
overhead, and **how many tests the model decided to write** — on the identical
bookshop task Fable 5 wrote 6 tests and Opus 5 wrote 104, a ~17x spread with the
language held constant. Model-authored tests also exercise different work, so
even "the slowest single test" is not the same operation across two runs.

WHAT THIS DOES INSTEAD. Run a **fixed, retort-authored probe** against the
finished artifact: the same operation, the same input, every implementation,
every language. That is the only way the number means "how fast is this program"
rather than "how verbose were its tests".

The probe per task is the task's own uniform contract:

  rest-api-crud  — start the server, then N identical HTTP round-trips
                   (POST /books + GET /books) against it.
  brazil-bench   — start the MCP server on stdio, then N identical
                   `tools/call` round-trips. Its cold start is also a real
                   measurement: every implementation loads the SAME six CSVs
                   (23,954 matches), so load time is directly comparable in a
                   way a test suite never is.
  cli-data-pipeline — pipe the SAME CSV through the same filter/sort/aggregate.

CONFOUNDERS THIS CONTROLS FOR, because otherwise the numbers are noise:

  * **JIT warm-up** — Java and C# are slow for the first iterations and then
    fast. WARMUP_ITERS are run and discarded, and the reported figure is the
    MEDIAN of the timed iterations, not the mean, so one stall does not set it.
  * **Cold start vs steady state** — reported separately. For a CLI tool the
    cold start IS the user experience; for a server it is a one-off. Collapsing
    them into one number would flatter servers and punish CLIs.
  * **Build time** — excluded. A compiled language must not be charged for
    `cargo build` in a latency figure. Build cost is `_duration_seconds`.
  * **A busy machine** — this measures wall clock, so a concurrent experiment
    corrupts it silently. `measure()` refuses to run while a `retort run` is
    alive rather than returning a plausible wrong number.

The score is a normalized 0..1 (fast → 1.0) so ANOVA can use it, but the raw
milliseconds are the point and are returned by `measure()` for the report.
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

#: Iterations run and thrown away before timing starts (JIT/page-cache warm-up).
WARMUP_ITERS = 3
#: Timed iterations. The reported steady-state figure is their median.
TIMED_ITERS = 10
#: A single probe iteration slower than this is treated as a non-result.
ITER_TIMEOUT_S = 30
#: Seconds to wait for a server probe to start listening / answer.
STARTUP_TIMEOUT_S = 60
#: Milliseconds at which the normalized score reaches 0.0.
SLOW_MS = 1000.0


@dataclass
class RuntimeResult:
    """Raw measurement. The milliseconds are the deliverable, not the score."""

    task: str
    language: str
    ok: bool
    cold_start_ms: float | None = None
    steady_median_ms: float | None = None
    steady_min_ms: float | None = None
    steady_max_ms: float | None = None
    iters: int = 0
    note: str = ""
    samples_ms: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "language": self.language,
            "ok": self.ok,
            "cold_start_ms": self.cold_start_ms,
            "steady_median_ms": self.steady_median_ms,
            "steady_min_ms": self.steady_min_ms,
            "steady_max_ms": self.steady_max_ms,
            "iters": self.iters,
            "note": self.note,
        }


def _machine_is_busy() -> bool:
    """True if an experiment is running — wall-clock timing would be garbage."""
    try:
        out = subprocess.run(
            ["pgrep", "-f", "retort run"], capture_output=True, text=True, timeout=10
        )
        return out.returncode == 0 and bool(out.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ---------------------------------------------------------------- brazil probe


#: The fixed exchange every brazil implementation must answer.
#:
#: `initialize` MUST carry `capabilities` and `clientInfo` — a stricter server
#: (the TypeScript one validates with zod) rejects the handshake without them,
#: and an earlier version of this probe omitted both and read the resulting
#: -32603 as "the server never answered".
#:
#: The second call is `tools/list`, NOT a named tool. Tool NAMES are chosen by
#: each implementation and are not pinned by the spec, so `tools/call` with a
#: fixed name would silently measure "did this run happen to pick that name"
#: rather than "how fast is this program". `tools/list` is protocol-guaranteed,
#: so it is the same request everywhere — and because these servers load all six
#: CSVs at start-up, the round-trip still includes the data load that makes the
#: number interesting.
BRAZIL_CALLS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "retort-runtime-probe", "version": "1"}}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
]


def _first_executable(*globs: Path) -> Path | None:
    for p in globs:
        if p.is_file() and p.stat().st_mode & 0o111 and "." not in p.name:
            return p
    return None


def _build_then_entry(run_dir: Path, language: str) -> tuple[list[str] | None, str]:
    """(command that starts the stdio server, note) — building first if needed.

    The BUILD IS UNTIMED and runs once, before any measurement: charging a
    compiled language for `cargo build` inside a latency figure would say more
    about the compiler than the program. Build cost already lives in
    `_duration_seconds`.

    Each entry is derived from the project's OWN manifest rather than a guessed
    convention — the binary name comes from Cargo.toml, the start command from
    package.json, the escript name from mix.exs. Where the manifest does not
    declare an entrypoint (clojure's deps.edn here has only a :test alias, and
    this erlang project ships no escript stanza), this returns None and the run
    is reported as an explicit non-result rather than measured wrongly.
    """
    def build(cmd: list[str], timeout: int = 600) -> bool:
        try:
            r = subprocess.run(cmd, cwd=run_dir, capture_output=True,
                               text=True, timeout=timeout)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    if language == "python":
        py = run_dir / "venv" / "bin" / "python"
        interp = str(py) if py.exists() else "python3"
        for f in ("server.py", "main.py"):
            if (run_dir / f).exists():
                return [interp, f], ""
        return None, "no server.py/main.py"

    if language == "go":
        if (run_dir / "go.mod").exists():
            if not build(["go", "build", "-o", ".retort-bin", "."]):
                return None, "go build failed"
            return [str(run_dir / ".retort-bin")], ""
        return None, "no go.mod"

    if language == "rust":
        toml = run_dir / "Cargo.toml"
        if not toml.exists():
            return None, "no Cargo.toml"
        if not build(["cargo", "build", "--release", "--quiet"]):
            return None, "cargo build failed"
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', toml.read_text(errors="replace"), re.M)
        if m:
            exe = run_dir / "target" / "release" / m.group(1)
            if exe.exists():
                return [str(exe)], ""
        exe = _first_executable(*sorted((run_dir / "target" / "release").glob("*")))
        return ([str(exe)], "") if exe else (None, "no release binary")

    if language == "typescript":
        pkg = run_dir / "package.json"
        if not pkg.exists():
            return None, "no package.json"
        try:
            scripts = json.loads(pkg.read_text()).get("scripts", {})
        except ValueError:
            scripts = {}
        # Archives strip node_modules AND dist (see cli._ARCHIVE_NOISE), so a
        # restore is required before the build — without it `npm run build`
        # fails silently and `npm start` dies on a missing dist/server.js,
        # which the probe would otherwise report as "the server never answered".
        if not (run_dir / "node_modules").exists():
            build(["npm", "install", "--silent"], timeout=600)
        if scripts.get("build") and not build(["npm", "run", "build", "--silent"]):
            return None, "npm run build failed after restore"
        start = scripts.get("start")
        if start:
            return ["npm", "start", "--silent"], ""
        return None, "package.json declares no start script"

    if language == "csharp":
        projs = [p for p in run_dir.glob("*.csproj") if "test" not in p.stem.lower()]
        if not projs:
            return None, "no non-test .csproj"
        if not build(["dotnet", "build", str(projs[0]), "--nologo", "-v", "q"]):
            return None, "dotnet build failed"
        return ["dotnet", "run", "--project", str(projs[0]), "--no-build", "--nologo"], ""

    if language == "elixir":
        mix = run_dir / "mix.exs"
        if not mix.exists():
            return None, "no mix.exs"
        text = mix.read_text(errors="replace")
        if "escript" not in text:
            return None, "mix.exs declares no escript entrypoint"
        if not build(["mix", "escript.build"]):
            return None, "mix escript.build failed"
        m = re.search(r"app:\s*:(\w+)", text)
        exe = run_dir / (m.group(1) if m else "")
        return ([str(exe)], "") if exe.exists() else (None, "escript not produced")

    if language in ("c", "cpp", "objc"):
        # C ships its server binary already; C++/ObjC usually need the build.
        exe = _first_executable(*sorted(run_dir.glob("*")))
        if exe and "test" not in exe.name.lower():
            return [str(exe)], ""
        if (run_dir / "Makefile").exists():
            build(["make"])
            exe = _first_executable(*sorted(run_dir.glob("*")))
            if exe and "test" not in exe.name.lower():
                return [str(exe)], ""
        return None, "no non-test executable produced"

    if language == "java":
        if not (run_dir / "pom.xml").exists():
            return None, "no pom.xml"
        if not build(["mvn", "-q", "-DskipTests", "package"], timeout=900):
            return None, "mvn package failed"
        jars = [p for p in (run_dir / "target").glob("*.jar")
                if "sources" not in p.name and "javadoc" not in p.name]
        return ([ "java", "-jar", str(jars[0])], "") if jars else (None, "no jar built")

    return None, f"no run recipe for {language!r}"


def _find_server_entry(run_dir: Path, language: str) -> list[str] | None:
    cmd, _ = _build_then_entry(run_dir, language)
    return cmd


def _probe_brazil(run_dir: Path, language: str) -> RuntimeResult:
    """Time N identical MCP tool calls, plus the one-off data load."""
    res = RuntimeResult(task="brazil-soccer-mcp", language=language, ok=False)
    cmd, why = _build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no recognizable server entrypoint — not guessed"
        return res

    payload = "\n".join(json.dumps(c) for c in BRAZIL_CALLS) + "\n"

    def one_shot() -> float | None:
        """One full start → initialize → tools/call → exit, in ms."""
        t0 = time.perf_counter()
        try:
            out = subprocess.run(
                cmd, cwd=run_dir, input=payload, capture_output=True,
                text=True, timeout=ITER_TIMEOUT_S,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        if '"result"' not in (out.stdout or ""):
            return None
        return (time.perf_counter() - t0) * 1000.0

    first = one_shot()
    if first is None:
        res.note = "server did not answer a tools/call probe"
        return res
    res.cold_start_ms = first

    for _ in range(WARMUP_ITERS):
        one_shot()
    samples = [ms for _ in range(TIMED_ITERS) if (ms := one_shot()) is not None]
    if not samples:
        res.note = "probe answered once then stopped"
        return res

    res.ok = True
    res.samples_ms = samples
    res.iters = len(samples)
    res.steady_median_ms = statistics.median(samples)
    res.steady_min_ms = min(samples)
    res.steady_max_ms = max(samples)
    return res


# -------------------------------------------------------------- bookshop probe


def _probe_bookshop(run_dir: Path, language: str) -> RuntimeResult:
    """Not implemented: needs a per-language server launch + port handshake.

    Returned as an explicit non-result rather than a zero. A zero here would be
    indistinguishable from an infinitely slow program, which is exactly the
    false-zero shape this repo keeps having to retract.
    """
    return RuntimeResult(
        task="rest-api-crud", language=language, ok=False,
        note="bookshop probe not implemented (needs server launch + port wait)",
    )


_PROBES = {
    "brazil-soccer-mcp": _probe_brazil,
    "rest-api-crud": _probe_bookshop,
}


def measure(run_dir: Path, task: str, language: str) -> RuntimeResult:
    """Measure one archived run. Refuses to guess and refuses a busy machine."""
    if _machine_is_busy():
        return RuntimeResult(
            task=task, language=language, ok=False,
            note="REFUSED: an experiment is running; wall-clock timing would be invalid",
        )
    probe = _PROBES.get(task)
    if probe is None:
        return RuntimeResult(task=task, language=language, ok=False,
                             note=f"no probe defined for task {task!r}")
    return probe(run_dir, language)


class RuntimeScorer:
    """Normalized 0..1 runtime score (fast → 1.0); raw ms via ``measure()``.

    Opt-in via the ``responses:`` list — it starts the produced program, which is
    far heavier than reading a file, and is only meaningful for tasks with a
    probe defined above.
    """

    @property
    def name(self) -> str:
        return "runtime"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0
        task = (getattr(artifacts, "task_name", "") or "").strip()
        result = measure(Path(artifacts.output_dir), task, stack.language)
        if not result.ok or result.steady_median_ms is None:
            return 0.0
        ms = result.steady_median_ms
        return max(0.0, min(1.0, 1.0 - (ms / SLOW_MS)))
