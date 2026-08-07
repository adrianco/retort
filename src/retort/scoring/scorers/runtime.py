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

import hashlib
import json
import os
import re
import selectors
import shutil
import statistics
import subprocess
import tempfile
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

#: Iterations run and thrown away before timing starts (JIT/page-cache warm-up).
WARMUP_ITERS = 3
#: Timed iterations. The reported steady-state figure is their median.
TIMED_ITERS = 10
#: A single probe iteration slower than this is treated as a non-result.
ITER_TIMEOUT_S = 30
#: Generous on purpose: for a lazily-loading implementation this ONE call pays
#: the entire 42k-row data load that an eager one paid before start-up.
QUERY_TIMEOUT_S = 120
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
    #: Time to answer a REAL data question (tools/call), not protocol metadata.
    #: This is the comparable number: see _first_query for why cold start is not.
    first_query_ms: float | None = None
    first_query_tool: str = ""
    note: str = ""
    samples_ms: list[float] = field(default_factory=list)
    #: How much data this implementation actually ingested, scraped from its own
    #: start-up banner. NOT a caveat on the timing — a dimension of the result,
    #: and READ IT CAREFULLY: fewer rows can mean a BETTER implementation.
    #:
    #: The five brazil match files overlap on purpose (BR-Football 2014-2023,
    #: Brasileirao_Matches 2012-2022, novo_campeonato 2003-2019), so the same
    #: real-world fixture appears 2-3 times. **23,954 is exactly the sum of the
    #: five files** — that number means NO deduplication, and the run that
    #: reported it double-counts: its own handshake answered "Corinthians 2022
    #: home: 44 matches" where the spec's worked example says 19.
    #:
    #: The Go run loaded 16,947 and is the CORRECT one. It canonicalises
    #: competitions across files and merges fixtures within a one-day window
    #: (sources disagree by a day: local kick-off vs UTC). Verified externally —
    #: it reports 8,404 Série A matches for 2003-2023 against 8,406 expected from
    #: real season sizes, and its own `dataset_info` reports no load failures.
    #:
    #: Both scored 12/12, because the pinned checklist asks whether a capability
    #: EXISTS and never whether its numbers are right (future-experiments §0).
    #:
    #: DO NOT RANK ON THIS FIELD ALONE, in either direction. A low count can be
    #: careful merging or a broken loader, and the two are indistinguishable
    #: without the dedup key that produced it — an early version of the reference
    #: script keyed on date+teams only, and on that basis this very Go run looked
    #: like it had lost 17% of the corpus. Use scripts/brazil_dedup_reference.py,
    #: compare against the row matching the run's OWN key, and prefer the run's
    #: self-report where it exposes one.
    rows_loaded: int | None = None
    #: Median latency of a request to an ALREADY-RUNNING server — the data load
    #: already paid. Separate from cold start because they answer different
    #: questions: cold start is runtime boot + parse (where compiled should win
    #: big), this is per-request work (where every language should look similar,
    #: and a big spread means a structural problem like re-parsing per call).
    request_median_ms: float | None = None
    banner: str = ""
    #: Tool names the server advertises — the other axis implementations differ
    #: on, and the reason the probe uses `tools/list` rather than a fixed name.
    tool_count: int | None = None

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
            "request_median_ms": self.request_median_ms,
            # The COMPARABLE pair. Cold start alone is not: `tools/list` is
            # protocol metadata, so an eager implementation answers it having
            # loaded 42k rows and a lazy one having loaded none. Adding the
            # first real tools/call puts the finish line in the same place.
            # Measured on one machine, same model, same task: lazy = 41 ms cold
            # + 461 ms first answer; eager = 1109 ms cold + 2 ms first answer.
            "first_query_ms": self.first_query_ms,
            "first_query_tool": self.first_query_tool,
            "total_to_answer_ms": (
                self.cold_start_ms + self.first_query_ms
                if self.cold_start_ms is not None and self.first_query_ms is not None
                else None
            ),
            "rows_loaded": self.rows_loaded,
            "tool_count": self.tool_count,
            "banner": self.banner,
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
#: The `notifications/initialized` line is REQUIRED, not decorative. The MCP
#: lifecycle is initialize -> initialized -> normal traffic, and a spec-faithful
#: server will not serve `tools/list` until it has seen the notification. Omitting
#: it made those servers sit silent, which the probe reported as "did not answer"
#: — the failure looked identical to a broken program.
BRAZIL_CALLS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "retort-runtime-probe", "version": "1"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
]


def _first_executable(*globs: Path) -> Path | None:
    for p in globs:
        if p.is_file() and p.stat().st_mode & 0o111 and "." not in p.name:
            return p
    return None


def _declared_deps(run_dir: Path) -> list[str]:
    """Third-party requirements this project declares, from its own manifest."""
    deps: list[str] = []
    pyproject = run_dir / "pyproject.toml"
    if pyproject.exists():
        txt = pyproject.read_text(errors="replace")
        m = re.search(r"^\s*dependencies\s*=\s*\[(.*?)\]", txt, re.S | re.M)
        if m:
            deps += re.findall(r'"([^"]+)"', m.group(1))
    for name in ("requirements.txt", "requirements-dev.txt"):
        req = run_dir / name
        if req.exists():
            for line in req.read_text(errors="replace").splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith("-"):
                    deps.append(line)
    return sorted({d for d in deps if not d.lower().startswith("pytest")})


def _probe_venv(deps: list[str]) -> Path | None:
    """A venv with `deps` installed, CACHED and SHARED across runs by dep-set.

    Built once per distinct dependency set under the runtime root, never inside
    the archived run — these live in the git repo and a per-run venv would both
    pollute it and cost a pip install per measurement.

    This exists because the probe previously ran archived Python code against the
    SYSTEM interpreter. 21 of 36 Python brazil runs import the real `mcp` SDK,
    which is not installed there, so every one of them was rejected as "no
    entrypoint" while the hand-rolled stdlib implementations measured fine. The
    survivors were not a sample of Python — they were a sample of "Python with
    nothing to import", which is the fastest-starting subset by construction.
    """
    key = hashlib.sha1("\n".join(deps).encode()).hexdigest()[:12]
    base = os.environ.get("RETORT_HOME")
    root = (Path(base).expanduser() if base else Path.home() / ".retort")
    venv_dir = root / "cache" / "probe-venvs" / key
    py = venv_dir / "bin" / "python"
    if py.exists():
        return py
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)],
                       capture_output=True, timeout=180, check=True)
        if deps:
            subprocess.run([str(py), "-m", "pip", "install", "-q", *deps],
                           capture_output=True, timeout=900, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        shutil.rmtree(venv_dir, ignore_errors=True)
        return None
    return py


def _cap_majors(deps: list[str]) -> list[str]:
    """Add an upper major bound to each unbounded `>=` requirement.

    These archives declare open-ended constraints (`mcp>=1.2`) and then age. The
    exp-46 Python run imports `mcp.server.fastmcp`, which mcp 2.0 removed — so
    resolving `mcp>=1.2` today installs 2.0.0 and the program that was correct
    when written no longer starts. Capping reproduces the era it was written in
    (1.29.0 here) instead of recording a wrong non-result.
    """
    out = []
    for d in deps:
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*>=\s*(\d+)", d)
        if m and "<" not in d and "," not in d:
            out.append(f"{d},<{int(m.group(2)) + 1}")
        else:
            out.append(d)
    return out


def _importable(py: Path, run_dir: Path, module: str) -> str:
    """"" if `module` imports cleanly, else the last line of the traceback."""
    try:
        r = subprocess.run([str(py), "-c", f"import {module}"], cwd=run_dir,
                           capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return str(exc)
    if r.returncode == 0:
        return ""
    return (r.stderr.strip().splitlines() or ["import failed"])[-1][:160]


def _python_entry(run_dir: Path) -> tuple[list[str] | None, str]:
    """Start command for a Python MCP server, in declared-entrypoint order.

    Order matters twice over.

    Opus consistently emits a PACKAGE layout (`brazilian_soccer/server.py`,
    importing `from .formatting import ...`), which cannot be started as a path
    — `python pkg/server.py` dies with "attempted relative import with no known
    parent package". It must be `-m`. An earlier version looked only for a
    TOP-LEVEL server.py/main.py and so rejected every package-structured run.

    And a declared console script is not automatically the server. One run
    declares only `brazilian-soccer-mcp = "brazilian_soccer.cli:main"`, an
    argparse CLI whose subcommand is REQUIRED, so calling `main()` exits with
    "the following arguments are required: command". The package's own
    `server` module is the server; a `.cli` entry point loses to it.
    """
    deps = _declared_deps(run_dir)

    # ---- resolve the entrypoint (independent of which venv we end up with) --
    module: str | None = None          # importable module, started with -m
    call: tuple[str, str] | None = None  # (module, function) console script
    script: str | None = None          # plain top-level script

    packages = sorted(d for d in run_dir.iterdir()
                      if d.is_dir() and (d / "__init__.py").exists())
    # __main__.py first: it is the canonical "run this package" and the author
    # wrote it deliberately. A `server` module is the next best signal.
    server_mod = None
    for pkg in packages:
        if (pkg / "__main__.py").exists():
            server_mod = pkg.name
            break
        for cand in ("server", "mcp_server"):
            if (pkg / f"{cand}.py").exists():
                server_mod = f"{pkg.name}.{cand}"
                break
        if server_mod:
            break

    pyproject = run_dir / "pyproject.toml"
    if pyproject.exists():
        txt = pyproject.read_text(errors="replace")
        m = re.search(r"^\s*\[project\.scripts\](.*?)(?=^\s*\[|\Z)", txt, re.S | re.M)
        if m:
            entries = re.findall(r'^\s*([\w.-]+)\s*=\s*"([\w.]+):(\w+)"', m.group(1), re.M)
            # A `.cli` module is a command-line front end, not the server; it
            # sorts last, and loses outright when the package has a server module.
            entries.sort(key=lambda e: (e[1].endswith(".cli"),
                                        "server" not in e[1] and "mcp" not in e[0]))
            if entries and not (entries[0][1].endswith(".cli") and server_mod):
                call = (entries[0][1], entries[0][2])

    if call is None and server_mod:
        module = server_mod
    if call is None and module is None:
        for f in ("server.py", "main.py", "mcp_server.py", "app.py"):
            if (run_dir / f).exists():
                script = f
                break
    if call is None and module is None and script is None:
        return None, "no python entrypoint (no [project.scripts], package, or server.py)"

    # ---- build a venv, and verify the entry actually IMPORTS in it ----------
    target = call[0] if call else (module or "")
    attempts: list[list[str]] = [deps]
    capped = _cap_majors(deps)
    if capped != deps:
        attempts.append(capped)

    last = ""
    for attempt in attempts:
        py = _probe_venv(attempt)
        if py is None:
            last = f"could not build a venv for deps: {', '.join(attempt) or 'none'}"
            continue
        if target:
            last = _importable(py, run_dir, target)
            if last:
                continue           # e.g. mcp 2.0 removed mcp.server.fastmcp
        interp = str(py)
        if call:
            return [interp, "-c", f"from {call[0]} import {call[1]}; {call[1]}()"], ""
        if module:
            return [interp, "-m", module], ""
        return [interp, script], ""      # type: ignore[list-item]
    return None, last or "python entry could not be imported"


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
    # ABSOLUTE, always. The returned command is executed with cwd=run_dir, so a
    # relative path like "experiments/.../target/release/server" resolves to
    # run_dir/experiments/... and vanishes. Popen then raises FileNotFoundError,
    # which the probe caught and reported as "server did not answer" — so every
    # compiled language (rust, c, cpp, objc, java, elixir, go) looked like a
    # broken program when the binary was fine and answered by hand.
    run_dir = run_dir.resolve()

    def build(cmd: list[str], timeout: int = 600) -> bool:
        try:
            r = subprocess.run(cmd, cwd=run_dir, capture_output=True,
                               text=True, timeout=timeout)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    if language == "python":
        return _python_entry(run_dir)

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
        # RECURSIVE. These solutions put projects under src/<Name>/<Name>.csproj,
        # so a top-level glob found nothing and reported "no non-test .csproj"
        # for a solution that builds and runs perfectly.
        projs = [p for p in run_dir.rglob("*.csproj")
                 if "test" not in p.stem.lower()
                 and ".retort" not in str(p)]
        # Prefer the project that actually produces an executable: a solution
        # here is typically Core (a library) + McpServer (Exe), and `dotnet run`
        # against the library fails.
        exe_projs = [p for p in projs
                     if "<OutputType>Exe</OutputType>"
                     in p.read_text(errors="replace").replace(" ", "")]
        projs = exe_projs or projs
        if not projs:
            return None, "no non-test .csproj"
        if not build(["dotnet", "build", str(projs[0]), "--nologo", "-v", "q"]):
            return None, "dotnet build failed"
        # Run the BUILT ASSEMBLY, not `dotnet run --project`. `dotnet run` sets
        # the working directory to the PROJECT directory (src/<Name>/), so a
        # server that resolves `data/kaggle` relative to cwd cannot find it and
        # exits with "could not locate the data/kaggle directory" — which is a
        # harness artefact, not a defect in the program. Every other language
        # here executes its artifact with cwd=run_dir; this makes C# match.
        dlls = [d for d in (projs[0].parent / "bin").rglob(f"{projs[0].stem}.dll")
                if "/ref/" not in str(d)]
        if dlls:
            return ["dotnet", str(sorted(dlls)[0])], ""
        return ["dotnet", "run", "--project", str(projs[0]), "--no-build", "--nologo"], ""

    if language == "elixir":
        mix = run_dir / "mix.exs"
        if not mix.exists():
            return None, "no mix.exs"
        text = mix.read_text(errors="replace")
        if "escript" not in text:
            return None, "mix.exs declares no escript entrypoint"
        # deps FIRST. `deps/` is not in the archive, so escript.build stops with
        # "Unchecked dependencies ... run mix deps.get" — a missing fetch step,
        # not a broken project.
        build(["mix", "deps.get"], timeout=600)
        if not build(["mix", "escript.build"]):
            return None, "mix escript.build failed (after deps.get)"
        # The escript's filename comes from `escript: [name: "..."]`, NOT from
        # `app: :...`. Here the app is :brazilian_soccer but the binary is
        # `brazilian_soccer_mcp`, so keying on the app name looked for a file
        # that was never going to exist and reported "escript not produced" for
        # a build that had just succeeded.
        m = re.search(r'escript:\s*\[[^\]]*name:\s*"([^"]+)"', text, re.S)
        if not m:
            m = re.search(r"app:\s*:(\w+)", text)
        exe = run_dir / (m.group(1) if m else "")
        if exe.is_file():
            return [str(exe)], ""
        # Fall back to whatever executable the build dropped at the root.
        cand = _first_executable(*sorted(run_dir.glob("*")))
        if cand is not None and "test" not in cand.name.lower():
            return [str(cand)], ""
        return None, "escript not produced"

    if language == "clojure":
        deps = run_dir / "deps.edn"
        if not deps.exists():
            return None, "no deps.edn"
        # PREFER A DECLARED ALIAS. Where deps.edn declares one, it names the
        # entrypoint the author intended: this project has both
        # `:mcp {:main-opts ["-m" "brazilian-soccer.server"]}` and a `:cli`
        # alias, and scanning the source for (defn -main ...) picked the CLI —
        # which starts, ignores stdin, and was recorded as "no reply to
        # tools/list". Rank server-ish aliases first and never take a test one.
        text = deps.read_text(errors="replace")
        aliases = re.findall(r":([\w-]+)\s*\{[^{}]*:main-opts\s*\[[^\]]*"
                             r'"-m"\s*"([\w.-]+)"', text)
        ranked = sorted(
            (a for a in aliases
             if "test" not in a[0].lower() and "test" not in a[1].lower()),
            key=lambda a: (0 if ("mcp" in a[0].lower() or "server" in a[1].lower())
                           else (2 if a[1].endswith(".cli") else 1)),
        )
        if ranked:
            alias, ns = ranked[0]
            return ["clojure", f"-M:{alias}"], ""

        # No usable alias — fall back to the source: find the file with
        # (defn -main ...) and convert its path to a namespace
        # (src/a_b/core.clj -> a-b.core; Clojure munges hyphens to underscores).
        for clj in sorted(run_dir.rglob("*.clj")):
            if "test" in clj.parts or "test" in clj.stem:
                continue
            try:
                if "(defn -main" not in clj.read_text(errors="replace"):
                    continue
            except OSError:
                continue
            rel = clj.relative_to(run_dir / "src") if (run_dir / "src") in clj.parents \
                else clj.relative_to(run_dir)
            ns = str(rel.with_suffix("")).replace("/", ".").replace("_", "-")
            return ["clojure", "-M", "-m", ns], ""
        return None, "no (defn -main ...) found in any .clj"

    if language == "erlang":
        if not (run_dir / "rebar.config").exists():
            return None, "no rebar.config"
        # PREFER THE PROJECT'S OWN ESCRIPT. Both erlang runs here declare
        # escript_main_app/escript_name in rebar.config and their READMEs say
        # `rebar3 escriptize`; one exports main/1, not a zero-arity entry, so the
        # `erl -s mod entry` path below could never start it and reported
        # "exports no zero-arity main/run entry" for a project that builds and
        # runs fine. Read the declared build, do not impose a convention.
        rebar_cfg = (run_dir / "rebar.config").read_text(errors="replace")
        if "escript_main_app" in rebar_cfg or "escript_name" in rebar_cfg:
            if build(["rebar3", "escriptize"], timeout=900):
                m = re.search(r"\{escript_name,\s*([\w']+)\}", rebar_cfg)
                name = m.group(1).strip("'") if m else None
                bins = [b for b in sorted((run_dir / "_build" / "default" / "bin").glob("*"))
                        if b.is_file()] if (run_dir / "_build" / "default" / "bin").is_dir() else []
                chosen = next((b for b in bins if name and b.name == name), None) or \
                    (bins[0] if bins else None)
                if chosen is not None:
                    return [str(chosen)], ""

        if not build(["rebar3", "compile"], timeout=600):
            return None, "rebar3 compile failed"
        # No escript stanza in this project, so run the beam directly. The entry
        # module is the one matching the app name.
        app = next(iter(sorted((run_dir / "src").glob("*.app.src"))), None)
        mod = app.name.replace(".app.src", "") if app else None
        ebins = sorted(run_dir.glob("_build/default/lib/*/ebin"))
        if not mod or not ebins:
            return None, "no app module or compiled ebin"
        # The entry function is NOT always main/0. This project exports run/0 and
        # its README says `erl ... -s brazilian_soccer_mcp run`; guessing "main"
        # started the VM, ran nothing, and the probe reported "did not answer".
        # Read the -export list instead of assuming a convention.
        entry = None
        src = run_dir / "src" / f"{mod}.erl"
        if src.exists():
            exports = " ".join(re.findall(r"-export\(\[([^\]]*)\]\)",
                                          src.read_text(errors="replace")))
            for cand in ("main", "run", "start_link", "start"):
                if re.search(rf"\b{cand}/0\b", exports):
                    entry = cand
                    break
        if entry is None:
            return None, f"{mod}.erl exports no zero-arity main/run entry"
        pa: list[str] = []
        for e in ebins:
            pa += ["-pa", str(e)]
        return ["erl", *pa, "-noshell", "-s", mod, entry], ""

    if language == "swift":
        pkg = run_dir / "Package.swift"
        if not pkg.exists():
            return None, "no Package.swift"
        if not build(["swift", "build", "-c", "release"], timeout=900):
            return None, "swift build -c release failed"
        m = re.search(r'\.executable\(\s*name:\s*"([^"]+)"', pkg.read_text(errors="replace"))
        cands = [run_dir / ".build" / "release" / m.group(1)] if m else []
        cands += sorted((run_dir / ".build" / "release").glob("*"))
        exe = _first_executable(*cands)
        return ([str(exe)], "") if exe else (None, "no release executable produced")

    if language in ("c", "cpp", "objc"):
        def find_exe() -> Path | None:
            """Search the OUTPUT DIRECTORIES, not just the run root.

            These Makefiles declare `BIN_DIR := bin` / `BUILD_DIR := build` and
            emit `bin/brsoccer-mcp`, `build/brazilian-soccer-mcp`. The probe only
            globbed the top level, so it reported "no non-test executable
            produced" for projects whose server binary was already sitting built
            on disk one directory down.
            """
            cands: list[Path] = []
            for d in (run_dir, run_dir / "bin", run_dir / "build",
                      run_dir / ".retort-build", run_dir / "out"):
                if d.is_dir():
                    cands += sorted(d.glob("*"))
            return _first_executable(*cands)

        makefile = run_dir / "Makefile"
        # Prefer the target the Makefile itself names as the server, rather than
        # whichever executable sorts first — `run-tests` and the server sit in
        # the same output directory.
        declared: Path | None = None
        if makefile.exists():
            m = re.search(r"^\s*SERVER\s*:?=\s*(\S+)", makefile.read_text(errors="replace"), re.M)
            if m:
                cand = run_dir / m.group(1).replace("$(BIN_DIR)", "bin").replace("$(BUILD_DIR)", "build")
                declared = cand if cand.is_file() else None

        exe = declared or find_exe()
        if exe and "test" not in exe.name.lower():
            return [str(exe)], ""
        if makefile.exists():
            build(["make"])
            if declared is None:
                m = re.search(r"^\s*SERVER\s*:?=\s*(\S+)", makefile.read_text(errors="replace"), re.M)
                if m:
                    cand = run_dir / m.group(1).replace("$(BIN_DIR)", "bin").replace("$(BUILD_DIR)", "build")
                    declared = cand if cand.is_file() else None
            exe = declared or find_exe()
            if exe and "test" not in exe.name.lower():
                return [str(exe)], ""
        cml = run_dir / "CMakeLists.txt"
        if cml.exists():
            # Build the SERVER target explicitly. A bare `cmake --build .` makes
            # every target, and the first executable found was `soccer_tests` —
            # timing the test binary instead of the program under measurement.
            targets = [n for n in re.findall(r"add_executable\(\s*([\w.-]+)",
                                             cml.read_text(errors="replace"))
                       if "test" not in n.lower()]
            bdir = run_dir / ".retort-build"
            if targets and build(["cmake", "-S", str(run_dir), "-B", str(bdir)]) \
                    and build(["cmake", "--build", str(bdir), "--target", targets[0]]):
                exe = _first_executable(*sorted(bdir.rglob(targets[0])))
                if exe:
                    return [str(exe)], ""
            return None, f"cmake build failed (targets: {targets or 'none non-test'})"
        return None, "no non-test executable produced"

    if language == "java":
        if not (run_dir / "pom.xml").exists():
            return None, "no pom.xml"
        if not build(["mvn", "-q", "-DskipTests", "package"], timeout=900):
            return None, "mvn package failed"
        # ORDER MATTERS, and the previous order was wrong. `java -cp
        # target/classes Main` omits every Maven dependency, so a project using
        # the MCP Java SDK died with NoClassDefFoundError before answering — and
        # with stderr discarded that read as "server did not answer". These
        # projects DO configure maven-shade-plugin, so `mvn package` already
        # produced a self-contained jar with a Main-Class; run that when it
        # exists. target/classes is the fallback for a project with no shade
        # plugin AND no dependencies, where a bare classpath is enough.
        shaded = [p for p in (run_dir / "target").glob("*.jar")
                  if not p.name.startswith("original-")
                  and "sources" not in p.name and "javadoc" not in p.name]
        for jar in shaded:
            try:
                with zipfile.ZipFile(jar) as zf:
                    manifest = zf.read("META-INF/MANIFEST.MF").decode(errors="replace")
            except (OSError, KeyError, zipfile.BadZipFile):
                continue
            if "Main-Class:" in manifest:
                return ["java", "-jar", str(jar)], ""

        main_cls = None
        for src in sorted((run_dir / "src" / "main" / "java").rglob("*.java")):
            try:
                if "public static void main" not in src.read_text(errors="replace"):
                    continue
            except OSError:
                continue
            rel = src.relative_to(run_dir / "src" / "main" / "java")
            main_cls = str(rel.with_suffix("")).replace("/", ".")
            break
        classes = run_dir / "target" / "classes"
        if main_cls and classes.is_dir():
            return ["java", "-cp", str(classes), main_cls], ""
        jars = [p for p in (run_dir / "target").glob("*.jar")
                if "sources" not in p.name and "javadoc" not in p.name]
        if jars:
            return ["java", "-jar", str(jars[0])], ""
        return None, "no main class on target/classes and no jar built"

    return None, f"no run recipe for {language!r}"


def _find_server_entry(run_dir: Path, language: str) -> list[str] | None:
    cmd, _ = _build_then_entry(run_dir, language)
    return cmd



def _readline_timeout(proc: subprocess.Popen, deadline: float) -> str | None:
    """A readline that actually honours a deadline. Returns None on timeout/EOF.

    `proc.stdout.readline()` BLOCKS FOREVER when a process produces no output and
    does not close its stdout — so a `while time.perf_counter() < deadline` loop
    around it never re-checks the clock and the timeout is decorative. One
    Erlang server that started but never answered held a sweep for 25 HOURS on
    exactly this, and the stuck beam.smp had to be killed by hand.

    select() on the pipe gives a real deadline: wait for readable-or-timeout,
    then read only when there is something to read.
    """
    sel = selectors.DefaultSelector()
    try:
        sel.register(proc.stdout, selectors.EVENT_READ)
    except (ValueError, OSError):
        return None
    try:
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return None
            if not sel.select(timeout=min(remaining, 1.0)):
                if proc.poll() is not None:      # died without output
                    return None
                continue
            line = proc.stdout.readline()
            return line if line else None
    except (OSError, ValueError):
        return None
    finally:
        sel.close()


#: Plausible values for a synthesized tools/call, keyed by what the parameter is
#: called. These are real entities in the corpus, so a correct implementation
#: returns data rather than an empty result.
_ARG_VALUES: list[tuple[tuple[str, ...], object]] = [
    (("team_a",), "Flamengo"),
    (("team_b",), "Palmeiras"),
    (("opponent",), "Palmeiras"),
    (("team", "club", "home", "away"), "Flamengo"),
    (("player", "scorer", "name"), "Neymar"),
    (("season", "year"), 2019),
    (("limit", "count", "top", "n"), 5),
    (("state", "uf"), "SP"),
    (("competition", "tournament", "league"), "Serie A"),
]

#: Tools whose name suggests they actually touch the match data. Ordered: the
#: first that answers wins. A tool like `list_teams` may be served from a small
#: index without ever loading the matches, which is exactly what we are trying
#: not to measure.
_QUERY_PREFERENCE = ("team_stats", "head_to_head", "find_matches", "match",
                     "team_profile", "stats", "search", "query", "get_")


def _stderr_file():
    """A temp file to catch the server's stderr.

    The probe used to run every server with stderr=DEVNULL, which threw away the
    single most useful artifact whenever one failed to start. A Java run that
    died with NoClassDefFoundError and a genuinely broken program produced the
    same note — "server did not answer" — so a harness bug was indistinguishable
    from a result. A FILE rather than a PIPE because nothing drains a pipe while
    the handshake is in flight, and a server that logs enough to fill it would
    deadlock.
    """
    return tempfile.TemporaryFile(mode="w+", errors="replace")


def _stderr_text(fh) -> str:
    try:
        fh.seek(0)
        return fh.read()
    except (OSError, ValueError):
        return ""


def _scrape_banner(text: str, captured: dict) -> None:
    """Pull "loaded N matches ..." out of an implementation's own start-up log."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("{"):
            continue
        m = re.search(r"(\d[\d,]{3,})\s+matches", line)
        if m:
            captured["rows"] = int(m.group(1).replace(",", ""))
            captured.setdefault("banner", line[:200])
            return
        if not captured.get("banner") and "load" in line.lower():
            captured["banner"] = line[:200]


def _stderr_tail(fh, limit: int = 300) -> str:
    try:
        fh.seek(0)
        text = fh.read().strip()
    except (OSError, ValueError):
        return ""
    if not text:
        return ""
    return text.splitlines()[-1][:limit]


def _mcp_handshake(proc, budget: float, captured: dict | None = None) -> dict | None:
    """initialize -> initialized -> tools/list, ONE MESSAGE AT A TIME.

    Sequential, and that is the whole point. This probe used to write all three
    handshake messages in a single burst and only then start reading. Several
    implementations read stdin into a buffer, parse the FIRST message in it, and
    drop whatever else arrived in the same read — so they answered `initialize`
    and then looked dead, which was recorded as "server did not answer".

    Measured on the same binaries: batched, C and Rust answer `[1]` and stall;
    one-at-a-time, both answer `[1, 2]` in under 5 s. **No real MCP client
    pipelines the handshake** — it sends `initialize`, waits for the reply, and
    only then continues — so the servers were right and the probe was wrong.
    That one difference accounted for most of the corpus being unmeasurable.

    Returns the tools/list response, or None.
    """
    deadline = time.perf_counter() + budget

    def send(obj) -> bool:
        try:
            proc.stdin.write(json.dumps(obj) + "\n")
            proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def await_id(want: int) -> dict | None:
        while time.perf_counter() < deadline:
            line = _readline_timeout(proc, deadline)
            if not line:
                return None
            stripped = line.strip()
            if not stripped.startswith("{"):
                # Human banner, not protocol — but KEEP it. These lines are where
                # implementations disclose how much they ingested ("loaded 16947
                # matches and 18207 players"), which is the variance this
                # measurement exists to expose.
                if stripped and captured is not None and not captured.get("banner"):
                    captured["banner"] = stripped[:200]
                    m = re.search(r"(\d[\d,]{3,})\s+matches", stripped)
                    if m:
                        captured["rows"] = int(m.group(1).replace(",", ""))
                continue
            try:
                msg = json.loads(stripped)
            except ValueError:
                continue
            if msg.get("id") == want:
                return msg
        return None

    if not send(BRAZIL_CALLS[0]):
        return None
    if await_id(1) is None:                  # WAIT before sending anything else
        return None
    if not send(BRAZIL_CALLS[1]):            # notification, no reply expected
        return None
    if not send(BRAZIL_CALLS[2]):
        return None
    listed = await_id(2)
    if listed is None or "error" in listed:
        return None
    if captured is not None:
        tools = (listed.get("result") or {}).get("tools")
        if isinstance(tools, list):
            captured["tool_count"] = len(tools)
    return listed


def _synthesize_args(schema: dict) -> dict:
    """Arguments satisfying a tool's REQUIRED properties, by parameter name."""
    props = schema.get("properties", {}) or {}
    args: dict = {}
    for key in schema.get("required", []) or []:
        spec = props.get(key, {}) or {}
        typ = spec.get("type", "string")
        val = None
        low = key.lower()
        for names, candidate in _ARG_VALUES:
            if any(n in low for n in names):
                val = candidate
                break
        if val is None:
            val = {"integer": 1, "number": 1, "boolean": False,
                   "array": [], "object": {}}.get(typ, "Flamengo")
        # honour the declared type even when the name matched
        if typ == "string" and not isinstance(val, str):
            val = str(val)
        elif typ in ("integer", "number") and not isinstance(val, (int, float)):
            val = 2019
        args[key] = val
    return args


def _pick_working_call(proc, listed: dict, budget: float,
                       await_id) -> tuple[str, dict, int] | None:
    """(tool name, arguments, next id) for a call this server actually answers.

    Shared by the first-query and per-request phases so both measure the same
    thing. Tools whose names suggest they touch match data are tried first: a
    `list_teams` may be served from a small index without ever reading the
    corpus, which is precisely what we are not trying to time.
    """
    tools = (listed.get("result") or {}).get("tools") or []

    def rank(tool: dict) -> int:
        name = tool.get("name", "").lower()
        for i, pref in enumerate(_QUERY_PREFERENCE):
            if pref in name:
                return i
        return len(_QUERY_PREFERENCE)

    rid = 700
    for tool in sorted(tools, key=rank)[:4]:
        rid += 1
        name = tool.get("name", "")
        args = _synthesize_args(tool.get("inputSchema", {}) or {})
        try:
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid,
                                         "method": "tools/call",
                                         "params": {"name": name,
                                                    "arguments": args}}) + "\n")
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            return None
        msg = await_id(rid, budget)
        if msg and "error" not in msg and not (msg.get("result") or {}).get("isError"):
            return name, args, rid + 1
    return None


def _first_query(cmd: list[str], run_dir: Path) -> tuple[float | None, str, str]:
    """(ms to answer a REAL data question, tool name, note).

    This exists because cold-start-to-`tools/list` is NOT comparable across
    implementations, and reading it as if it were produced a 29x "difference"
    between two runs of the SAME model on the SAME task.

    The cause: `tools/list` is protocol metadata. An implementation that loads
    all 42k rows at import answers it having done the work; one that streams
    lazily (`yield from csv.DictReader(...)`) answers it having done none. The
    clock stops at a different point in the work for each, so the fast number was
    partly just "this one deferred the load past the finish line".

    Issuing a real `tools/call` moves the finish line to the same place for
    everyone: whoever has not loaded the data yet pays for it here. Tool names
    are not pinned by the spec, so the tool and its arguments are synthesized
    from the server's OWN advertised schema.
    """
    try:
        proc = subprocess.Popen(
            cmd, cwd=run_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
    except (FileNotFoundError, OSError):
        return None, "", "could not start server"

    def send(obj) -> bool:
        try:
            proc.stdin.write(json.dumps(obj) + "\n")
            proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def await_id(want: int, budget: float) -> dict | None:
        deadline = time.perf_counter() + budget
        while time.perf_counter() < deadline:
            line = _readline_timeout(proc, deadline)
            if not line:
                return None
            s = line.strip()
            if not s.startswith("{"):
                continue                      # start-up banner, not a response
            try:
                msg = json.loads(s)
            except ValueError:
                continue
            if msg.get("id") == want:
                return msg
        return None

    try:
        listed = _mcp_handshake(proc, ITER_TIMEOUT_S)
        if not listed:
            return None, "", "did not complete the MCP handshake"
        tools = (listed.get("result") or {}).get("tools") or []
        if not tools:
            return None, "", "server advertises no tools"

        def rank(tool: dict) -> int:
            name = tool.get("name", "").lower()
            for i, pref in enumerate(_QUERY_PREFERENCE):
                if pref in name:
                    return i
            return len(_QUERY_PREFERENCE)

        tried = 0
        for tool in sorted(tools, key=rank):
            if tried >= 4:
                break
            tried += 1
            name = tool.get("name", "")
            args = _synthesize_args(tool.get("inputSchema", {}) or {})
            rid = 500 + tried
            t0 = time.perf_counter()
            if not send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                         "params": {"name": name, "arguments": args}}):
                return None, "", "server closed during tools/call"
            msg = await_id(rid, QUERY_TIMEOUT_S)
            ms = (time.perf_counter() - t0) * 1000.0
            if msg is None:
                continue
            if "error" in msg:
                continue                      # wrong args for this tool; try another
            result = msg.get("result") or {}
            if result.get("isError"):
                continue
            return ms, name, ""
        return None, "", f"no tool answered a synthesized call (tried {tried})"
    except (BrokenPipeError, OSError):
        return None, "", "server died during query"
    finally:
        try:
            proc.kill()
        except OSError:
            pass


def _serve_latency(cmd: list[str], run_dir: Path) -> float | None:
    """Median per-request latency against ONE already-warm process, in ms.

    Distinct from cold start on purpose. Cold start measures runtime boot + data
    load, where a native binary should beat an interpreter by a lot. THIS
    measures answering a request once the data is already in memory, which is a
    few microseconds of real work in any language — so a large spread here would
    mean something structural (per-request re-parsing, no index), not "compiled
    versus interpreted".
    """
    try:
        proc = subprocess.Popen(
            cmd, cwd=run_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
    except (FileNotFoundError, OSError):
        return None
    try:
        # Handshake once; the data load is paid here and excluded from the samples.
        listed = _mcp_handshake(proc, ITER_TIMEOUT_S)
        if listed is None:
            return None

        def await_id(want: int, budget: float) -> dict | None:
            deadline = time.perf_counter() + budget
            while time.perf_counter() < deadline:
                line = _readline_timeout(proc, deadline)
                if not line:
                    return None
                s = line.strip()
                if not s.startswith("{"):
                    continue
                try:
                    msg = json.loads(s)
                except ValueError:
                    continue
                if msg.get("id") == want:
                    return msg
            return None

        # Repeat a REAL query, not `tools/list`. tools/list is protocol
        # metadata whose response size scales with how many tools the
        # implementation chose to expose, and the models differ a lot there
        # (median 6 tools for terra, 16 for opus). Timing it therefore partly
        # measured "how big is your tool catalogue" — measured r = 0.37 between
        # tool count and the old per-request figure. A real tools/call with the
        # data already in memory is the per-request work we actually mean.
        picked = _pick_working_call(proc, listed, QUERY_TIMEOUT_S, await_id)
        if picked is None:
            return None
        tool_name, tool_args, next_id = picked

        samples: list[float] = []
        for i in range(TIMED_ITERS + WARMUP_ITERS):
            req = {"jsonrpc": "2.0", "id": next_id + i, "method": "tools/call",
                   "params": {"name": tool_name, "arguments": tool_args}}
            t0 = time.perf_counter()
            try:
                proc.stdin.write(json.dumps(req) + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                break
            if await_id(next_id + i, ITER_TIMEOUT_S) is None:
                break
            ms = (time.perf_counter() - t0) * 1000.0
            if i >= WARMUP_ITERS:          # discard warm-up
                samples.append(ms)
        return statistics.median(samples) if samples else None
    except (BrokenPipeError, OSError):
        return None
    finally:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


#: Words that mark a documented command as BUILD/TEST rather than "start it".
_NOT_A_RUN = ("test", "spec", "lint", "fmt", "format", "install", "deps.get",
              "compile", "escriptize", "clean", "bench", "coverage", "check",
              "eunit", "pytest", "publish", "docker", "git ", "curl", "chmod",
              "build", "--help", "--version")
#: First tokens that plausibly START something.
_RUNNERS = ("python", "python3", "node", "java", "dotnet", "erl", "escript",
            "clojure", "clj", "swift", "go", "cargo", "mix", "npm", "npx",
            "./", "bin/", "make", "elixir", "iex", "rebar3")


def _readme_commands(run_dir: Path) -> list[list[str]]:
    """Commands the project's OWN README gives for starting the server.

    Added because every single launch failure found in this corpus was the same
    mistake: the probe imposed a convention where the project had DECLARED the
    answer. C# said `<OutputType>Exe</OutputType>`, the C Makefile said
    `SERVER := bin/brsoccer-mcp`, rebar.config said `escript_main_app`, mix.exs
    said `escript: [name: ...]`, deps.edn said `:mcp {:main-opts ...}` — and
    each project's README said it in plain text as well. The erlang one reads
    `rebar3 escriptize     # build the server binary`.

    Used as a VERIFIED FALLBACK, not as the primary source: a README can be
    aspirational or stale, so a command from here is only accepted if it
    actually completes the MCP handshake. That keeps the manifest-driven recipes
    authoritative while stopping a convention mismatch from being recorded as a
    dead program.
    """
    import shlex

    text = ""
    for name in ("README.md", "README", "README.txt", "RUNNING.md", "USAGE.md"):
        f = run_dir / name
        if f.is_file():
            text += f.read_text(errors="replace") + "\n"
    if not text:
        return []

    lines: list[str] = []
    for block in re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S):
        lines += block.splitlines()
    lines += [m for m in re.findall(r"`([^`\n]{4,120})`", text)]

    out: list[list[str]] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.strip().lstrip("$").strip()
        line = line.split("#")[0].strip()          # drop trailing comments
        if not line or "\n" in line or "|" in line or "&&" in line:
            continue
        low = line.lower()
        # `make run` / `npm start` / `go run .` are runs despite the verb.
        is_explicit_run = any(low.startswith(p) for p in (
            "make run", "make serve", "make start", "make server",
            "npm start", "npm run start", "go run", "cargo run",
            "dotnet run", "mix run", "iex -s"))
        if not is_explicit_run and any(w in low for w in _NOT_A_RUN):
            continue
        if not (low.startswith(_RUNNERS) or (run_dir / line.split()[0]).exists()):
            continue
        try:
            argv = shlex.split(line)
        except ValueError:
            continue
        if not argv or line in seen:
            continue
        if argv == ["make"]:          # bare `make` is the default BUILD target
            continue
        seen.add(line)
        # Resolve a relative artifact path against the run dir; the command is
        # executed with cwd=run_dir but Popen resolves argv[0] against OUR cwd.
        cand = run_dir / argv[0]
        if cand.exists():
            argv[0] = str(cand)
        out.append(argv)
        if len(out) >= 4:
            break
    return out


def _probe_brazil(run_dir: Path, language: str) -> RuntimeResult:
    """Time N identical MCP tool calls, plus the one-off data load."""
    res = RuntimeResult(task="brazil-soccer-mcp", language=language, ok=False)
    cmd, why = _build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no recognizable server entrypoint — not guessed"
        return res

    captured: dict = {}
    #: Why the last one_shot() gave up. Without this the note was always the
    #: generic "server did not answer", which is what made a harness bug and a
    #: broken program indistinguishable in the results.
    failure: dict = {}

    def one_shot(cmd: list[str]) -> float | None:
        """Start -> handshake -> tools/list answered, in ms. Then kill the server.

        Deliberately does NOT wait for the process to exit. A stdio MCP server is
        a SERVER: several of these keep running after answering rather than
        closing on EOF, so waiting for exit timed out and was recorded as "the
        server never answered" — a false negative that hid every Go, Java and
        Rust cell. Stop the clock when the reply to request id 2 arrives, which
        is the thing being measured, then terminate.
        """
        t0 = time.perf_counter()
        errf = _stderr_file()
        try:
            proc = subprocess.Popen(
                cmd, cwd=run_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=errf, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError) as exc:
            failure["why"] = f"could not start: {exc}"
            errf.close()
            return None
        try:
            listed = _mcp_handshake(proc, ITER_TIMEOUT_S, captured)
            if listed is None:
                tail = _stderr_tail(errf)
                failure["why"] = tail or "no reply to tools/list"
                return None
            elapsed = (time.perf_counter() - t0) * 1000.0
            # Scrape the start-up banner from STDERR as well as stdout. A
            # correct MCP server keeps stdout pure protocol and logs to stderr,
            # so scanning only stdout meant `rows_loaded` was null for all 53
            # runs -- the very field needed to check whether an implementation
            # deduplicated the five overlapping match files.
            if captured.get("rows") is None:
                _scrape_banner(_stderr_text(errf), captured)
            return elapsed
        except (BrokenPipeError, OSError) as exc:
            failure["why"] = _stderr_tail(errf) or str(exc)
            return None
        finally:
            errf.close()
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    # Try the manifest-derived command first, then whatever the project's OWN
    # README says. Every launch failure in this corpus was the probe imposing a
    # convention on a project that had declared the answer; a README command is
    # accepted only if it completes the handshake, so a stale README cannot
    # inject a wrong measurement.
    candidates: list[list[str]] = [cmd]
    for extra in _readme_commands(run_dir):
        if extra not in candidates:
            candidates.append(extra)

    first = None
    for candidate in candidates:
        first = one_shot(candidate)
        if first is not None:
            if candidate is not cmd:
                res.note = ("launched via the command documented in the "
                            f"project README: {' '.join(candidate[:4])}")
            cmd = candidate
            break
    if first is None:
        res.note = f"did not complete the MCP handshake: {failure.get('why', 'no output')}"
        return res
    res.cold_start_ms = first

    # PHASE 1 — COLD START, repeated. Each one_shot() is a FULL process launch:
    # boot the runtime, parse the CSVs, answer once, die. This is the number that
    # separates a native binary from an interpreter, because it is dominated by
    # runtime start-up plus parsing ~24k rows — not by the trivial round-trip.
    for _ in range(WARMUP_ITERS):
        one_shot(cmd)
    samples = [ms for _ in range(TIMED_ITERS) if (ms := one_shot(cmd)) is not None]
    if not samples:
        res.note = f"answered once then stopped: {failure.get('why', 'no output')}"
        return res

    # PHASE 2 — PER-REQUEST latency against ONE LIVE process.
    # Until now this scorer restarted the server for every iteration, so its
    # "steady median" was just the cold start measured again — python read 267 ms
    # cold and 260 ms "steady", which is the same number twice, not two metrics.
    # Serving latency needs the process kept alive and asked repeatedly.
    res.request_median_ms = _serve_latency(cmd, run_dir)
    res.first_query_ms, res.first_query_tool, q_note = _first_query(cmd, run_dir)
    if res.first_query_ms is None and q_note and not res.note:
        res.note = f"cold start measured; first-query not: {q_note}"

    res.ok = True
    res.rows_loaded = captured.get("rows")
    res.banner = captured.get("banner", "")
    res.tool_count = captured.get("tool_count")
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


def measure(run_dir: Path, task: str, language: str, *,
            allow_busy: bool = False) -> RuntimeResult:
    """Measure one run. Refuses to guess, and refuses a busy machine.

    ``allow_busy`` is for the INLINE path only. Scoring happens inside the
    experiment, so `retort run` is by definition alive and the guard would
    refuse every cell. The guard still matters for the offline/report path,
    where a concurrent experiment really would corrupt the numbers — and this
    repo's one-experiment-at-a-time rule means an inline measurement still has
    the machine to itself.
    """
    if not allow_busy and _machine_is_busy():
        return RuntimeResult(
            task=task, language=language, ok=False,
            note="REFUSED: an experiment is running; wall-clock timing would be invalid",
        )
    probe = _PROBES.get(task)
    if probe is None:
        return RuntimeResult(task=task, language=language, ok=False,
                             note=f"no probe defined for task {task!r}")
    return probe(run_dir, language)


def detect_task(run_dir: Path) -> str:
    """Identify the task from the seeded workspace.

    ``RunArtifacts`` carries no task name and ``StackConfig`` only knows the
    factor levels, so rather than re-plumb every caller the task is read off the
    workspace retort itself seeded. TASK.md is written into every workspace and
    is the authoritative statement of what was asked.
    """
    if (run_dir / "brazilian-soccer-mcp-guide.md").exists() or \
            (run_dir / "data" / "kaggle").is_dir():
        return "brazil-soccer-mcp"
    task_md = run_dir / "TASK.md"
    if task_md.exists():
        text = task_md.read_text(errors="replace").lower()
        if "book collection" in text or "/books" in text:
            return "rest-api-crud"
        if "data pipeline" in text or "aggregate" in text and "csv" in text:
            return "cli-data-pipeline"
    return ""


class RuntimeScorer:
    """Normalized 0..1 runtime score (fast → 1.0); raw ms via ``measure()``.

    RUNS INLINE, during scoring, while the playpen workspace is still intact.
    That placement is the whole point: archived runs have had ``dist/``,
    ``build/``, ``target/`` and ``node_modules/`` stripped by
    ``cli._ARCHIVE_NOISE``, so measuring one means restoring and rebuilding a
    tree that is no longer what the agent actually ran. Inline, the built
    artifact is right there.

    Opt-in via the ``responses:`` list — it starts the produced program, which is
    far heavier than reading a file, and only tasks with a probe yield a number.
    """

    @property
    def name(self) -> str:
        return "runtime"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float | None:
        """Normalized score, or None when this run cannot be measured.

        None, never 0.0. A zero would enter the data as "infinitely slow" and be
        averaged into per-language means as if it were a real measurement — so a
        language whose probe simply failed would look like the slowest language
        rather than an absent one. This repo has already published two wrong
        conclusions from exactly that shape (the /var playpen the agent could not
        write to, and a Python cold start that was really a sampling artifact).
        The raw JSON is still written either way, carrying `note` so the reason
        is recoverable.
        """
        if not artifacts.succeeded or artifacts.output_dir is None:
            return None
        run_dir = Path(artifacts.output_dir)
        result = measure(run_dir, detect_task(run_dir), stack.language,
                         allow_busy=True)
        # Stash the raw measurement alongside the run so the milliseconds
        # survive, not just the normalized score — the ms are the deliverable.
        try:
            (run_dir / "_runtime.json").write_text(json.dumps(result.as_dict(), indent=1))
        except OSError:
            pass
        if not result.ok or result.steady_median_ms is None:
            return None
        ms = result.steady_median_ms
        return max(0.0, min(1.0, 1.0 - (ms / SLOW_MS)))
