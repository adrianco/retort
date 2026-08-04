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

    if language == "clojure":
        deps = run_dir / "deps.edn"
        if not deps.exists():
            return None, "no deps.edn"
        # deps.edn here declares only a :test alias, so the main namespace has to
        # come from the source: find the file with (defn -main ...) and convert
        # its path to a namespace (src/a_b/core.clj -> a-b.core; Clojure munges
        # hyphens to underscores on disk).
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
        # C ships its server binary already; C++/ObjC usually need the build.
        exe = _first_executable(*sorted(run_dir.glob("*")))
        if exe and "test" not in exe.name.lower():
            return [str(exe)], ""
        if (run_dir / "Makefile").exists():
            build(["make"])
            exe = _first_executable(*sorted(run_dir.glob("*")))
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
        # `java -jar` needs a Main-Class in the manifest, and a plain `mvn
        # package` without a shade/assembly plugin does not write one — the jar
        # here fails with "no main manifest attribute". So prefer running the
        # class directly off target/classes, discovering it from the source
        # rather than assuming a name.
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
        for call in BRAZIL_CALLS:
            proc.stdin.write(json.dumps(call) + "\n")
        proc.stdin.flush()
        deadline = time.perf_counter() + ITER_TIMEOUT_S
        while time.perf_counter() < deadline:
            line = proc.stdout.readline()
            if not line:
                return None
            s = line.strip()
            if s.startswith("{"):
                try:
                    if json.loads(s).get("id") == 2:
                        break
                except ValueError:
                    continue
        else:
            return None

        samples: list[float] = []
        for i in range(TIMED_ITERS + WARMUP_ITERS):
            req = {"jsonrpc": "2.0", "id": 100 + i, "method": "tools/list"}
            t0 = time.perf_counter()
            try:
                proc.stdin.write(json.dumps(req) + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                break
            got = False
            deadline = time.perf_counter() + ITER_TIMEOUT_S
            while time.perf_counter() < deadline:
                line = proc.stdout.readline()
                if not line:
                    break
                s = line.strip()
                if not s.startswith("{"):
                    continue
                try:
                    msg = json.loads(s)
                except ValueError:
                    continue
                if msg.get("id") == 100 + i:
                    got = True
                    break
            if not got:
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


def _probe_brazil(run_dir: Path, language: str) -> RuntimeResult:
    """Time N identical MCP tool calls, plus the one-off data load."""
    res = RuntimeResult(task="brazil-soccer-mcp", language=language, ok=False)
    cmd, why = _build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no recognizable server entrypoint — not guessed"
        return res

    payload = "\n".join(json.dumps(c) for c in BRAZIL_CALLS) + "\n"
    captured: dict = {}

    def one_shot() -> float | None:
        """Start → handshake → tools/list answered, in ms. Then kill the server.

        Deliberately does NOT wait for the process to exit. A stdio MCP server is
        a SERVER: several of these keep running after answering rather than
        closing on EOF, so waiting for exit timed out and was recorded as "the
        server never answered" — a false negative that hid every Go, Java and
        Rust cell. Stop the clock when the reply to request id 2 arrives, which
        is the thing being measured, then terminate.

        Stdout is read LINE BY LINE and non-JSON lines are skipped, because
        implementations print human banners first (the Go one emits
        "loaded 16947 matches ... in 134ms" before any JSON).
        """
        t0 = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd, cwd=run_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError):
            return None
        try:
            proc.stdin.write(payload)
            proc.stdin.flush()
            deadline = time.perf_counter() + ITER_TIMEOUT_S
            while time.perf_counter() < deadline:
                line = proc.stdout.readline()
                if not line:
                    return None
                stripped = line.strip()
                if not stripped.startswith("{"):
                    # Human banner, not protocol — but KEEP it. These lines are
                    # where implementations disclose how much they ingested
                    # ("loaded 16947 matches and 18207 players"), which is the
                    # variance this measurement exists to expose.
                    if stripped and not captured.get("banner"):
                        captured["banner"] = stripped[:200]
                        m = re.search(r"(\d[\d,]{3,})\s+matches", stripped)
                        if m:
                            captured["rows"] = int(m.group(1).replace(",", ""))
                    continue
                try:
                    msg = json.loads(stripped)
                except ValueError:
                    continue
                if msg.get("id") == 2 and "result" in msg:
                    tools = (msg.get("result") or {}).get("tools")
                    if isinstance(tools, list):
                        captured["tool_count"] = len(tools)
                    return (time.perf_counter() - t0) * 1000.0
                if msg.get("id") == 2 and "error" in msg:
                    return None
            return None
        except (BrokenPipeError, OSError):
            return None
        finally:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    first = one_shot()
    if first is None:
        res.note = "server did not answer a tools/call probe"
        return res
    res.cold_start_ms = first

    # PHASE 1 — COLD START, repeated. Each one_shot() is a FULL process launch:
    # boot the runtime, parse the CSVs, answer once, die. This is the number that
    # separates a native binary from an interpreter, because it is dominated by
    # runtime start-up plus parsing ~24k rows — not by the trivial round-trip.
    for _ in range(WARMUP_ITERS):
        one_shot()
    samples = [ms for _ in range(TIMED_ITERS) if (ms := one_shot()) is not None]
    if not samples:
        res.note = "probe answered once then stopped"
        return res

    # PHASE 2 — PER-REQUEST latency against ONE LIVE process.
    # Until now this scorer restarted the server for every iteration, so its
    # "steady median" was just the cold start measured again — python read 267 ms
    # cold and 260 ms "steady", which is the same number twice, not two metrics.
    # Serving latency needs the process kept alive and asked repeatedly.
    res.request_median_ms = _serve_latency(cmd, run_dir)

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

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded or artifacts.output_dir is None:
            return 0.0
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
            return 0.0
        ms = result.steady_median_ms
        return max(0.0, min(1.0, 1.0 - (ms / SLOW_MS)))
