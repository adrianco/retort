# Runtime measurement — how retort times the code a model produced

Every other response in retort scores the *artifact*: does it pass, is it
idiomatic, how many tokens did it cost. `runtime` scores the *program* — it
starts what the model built and times it. This document is the operating manual:
what is measured, what the numbers mean, how to add a language or a task, and
which mistakes have already been made here so they are not made again.

## Running it

`runtime` is part of the standard `responses:` set, so a normal `retort run`
produces performance data for every language that has a probe:

```yaml
responses:
  - code_quality
  - token_efficiency
  - test_coverage
  - runtime
```

**It must run inline, during the run.** It cannot be recovered afterwards by
re-scoring an archive: `cli._ARCHIVE_NOISE` strips `build/`, `target/`, `dist/`
and `node_modules/` when a run is archived, so an archived tree is not the tree
the agent produced. `retort rebuild` exists to measure archives anyway, but it
rebuilds from source, which is a different thing from what ran.

Each run writes `_runtime.json` beside its artifacts. The normalized 0..1 score
goes into the response vector; **the milliseconds in the JSON are the
deliverable**, not the score.

## The two numbers, and why one of them is a trap

| field | what it measures |
|---|---|
| `cold_start_ms` | process launch → answers `tools/list` |
| `first_query_ms` | → answers a real `tools/call` |
| `total_to_answer_ms` | the sum. **This is the comparable one.** |
| `request_median_ms` | per-request latency against one warm process, **repeating a real `tools/call`** |

**`request_median_ms` repeats a real query, not `tools/list`.** It used to repeat
`tools/list`, whose response size scales with how many tools an implementation
chose to expose — median 6 for Terra, 16 for Opus — so it partly measured
catalogue size rather than per-call work (r = 0.37 against tool count). The worst
outlier fell from 2.680 ms to 0.259 ms once measured properly, and the model
ranking inverted.

**Cold start alone is not comparable across implementations.** `tools/list` is
protocol metadata. An implementation that loads all 42k rows at import answers it
having done the work; one that streams lazily answers it having done none. The
clock stops at a different point in the job for each program.

Measured on one machine, same model, same task, two runs differing only in
thinking level:

| | cold start | first real query | total |
|---|---:|---:|---:|
| lazy — `yield from csv.DictReader(...)` | 41 ms | 461 ms | ~502 ms |
| eager — `rows = list(csv.DictReader(...))` | 1109 ms | 2 ms | ~1111 ms |

Cold start calls these **27x apart**. Time-to-first-answer calls them **2.2x
apart, in the other direction**. Reporting cold start as "the runtime of language
X" rewards deferring work past the finish line.

The `tools/call` is synthesized from each server's **own advertised schema** —
MCP does not pin tool names, so a fixed name would measure "did this run happen
to choose that name". Arguments are filled by parameter name (`team` →
`"Flamengo"`, `season` → `2019`) with the declared type honoured, and tools whose
names suggest they touch match data are tried first; `list_teams` may be served
from a small index without ever loading the corpus.

## Non-results are NULL, never zero

A run the probe cannot measure returns `None`, and the collector omits the metric
so it lands as NULL. **Do not "fix" this by returning 0.0.** A zero enters
aggregation as a real measurement meaning *infinitely slow*, so a language whose
probe merely failed becomes the slowest language in the table rather than an
absent one.

This is the single most repeated bug in this project. It has produced published
wrong conclusions at least three times: the `/var` playpen where the agent's file
tool was silently refused (read as a capability wall), a Python cold start that
was really a sampling artifact, and every scorer false-zero listed in
`test_coverage.py`. A failing program and a broken measurement look identical in
the output — the only defence is to keep them in different columns.

When a run is not measured, `note` in `_runtime.json` says why.

## One budget, and a hang is terminal

Every phase of one run's measurement draws on a single `_Budget`
(`PROBE_BUDGET_S`, plus `FACTUAL_BUDGET_S` for the factual check). The
per-iteration timeouts do not bound their own sum: 13 relaunches at
`ITER_TIMEOUT_S`, plus `first_query`, `serve_latency` and the factual probe's six
candidate calls, is **~19 minutes of scoring for one cell whose server never
answers** — longer than the agent took to write it. An 11-cell experiment can
spend more wall-clock scoring than running. A phase that runs out of budget
yields the samples it collected; the rest are non-results, never zeros.

**A timeout is evidence, not bad luck.** Measured cold starts here run 40 ms to
~3 s. A server given 30 s to answer `tools/list` is not slow, it is a program
that will not answer, and relaunching the identical command twelve more times
cannot turn that into a measurement. One timeout stops the loop. A *fast*
failure is different and is treated differently: a crash or `FileNotFoundError`
means the **command** was wrong, so the project's own README command is tried; a
hang means the **server** is at fault, so it is not.

## Dependency resolution — record it, don't override a declared bound

`_cap_majors` adds an upper major bound to **unbounded** `>=` requirements only.
`mcp>=1.2` is not a claim that the newest major works, it is the *absence* of a
claim, and the code was written against whatever was current at the time —
resolving to the latest major reproduces a different program. Capping preserves
the era.

**A declared upper bound is a claim, and it is left alone.** This was tested
against a real failure. exp-58's sol/python rep3 declares `mcp>=1.28,<3`, uses
the low-level `@server.list_tools()` decorator, resolves to mcp 2.0.0 — which
removed both `Server.list_tools` and `Server.call_tool` — and dies with
`AttributeError`. Recorded as a factual_accuracy failure.

That verdict **stands**, and its two siblings are the proof. Same model, same
task, same day, same probe:

| rep | declared | resolved | verdict |
|---|---|---|---|
| rep1 | `mcp>=1.2,<2` | 1.29.0 | passes |
| rep2 | `mcp>=2,<3` | 2.0.0 | passes — wrote 2.x code *and* pinned 2.x |
| rep3 | `mcp>=1.28,<3` | 2.0.0 | fails — wrote 1.x code, permitted 2.x |

exp-59's two python reps both declare `mcp>=1.28.1,<2` and pass. The model can
write a manifest that matches its code, and demonstrably did, in both
directions. rep3 shipped a version range its own code does not satisfy — a real
reproducibility defect in the deliverable, not an artifact of resolving late.
Capping it to `<2` would have hidden that by overruling the run's own stated
constraint, which is the opposite of what the unbounded case justifies.

**So the versions are RECORDED, not overridden.** `_venv_freeze` writes what was
actually installed into `deps` in both `_runtime.json` and `_factual.json`,
alongside the declared requirement, whether the cap applied, and each attempt.
Before this, the verdict held only the `AttributeError`, so a reader could not
tell a model defect from a resolver artifact — the same reason the factual gate
now stores the server's raw answer. **If you change `_cap_majors`' policy, write
the justification here first.**

## Kill the process group, not the launcher

`proc.kill()` kills the process it was handed. For `npm start` that is npm, not
the node server npm forked; for `mix run` it is mix, not the BEAM. The server is
reparented to init and keeps running — this repo had a C MCP server from exp-56
still alive **thirteen days** after the probe that started it.

A leaked server holds memory and a port while later cells are being *timed*, so
it corrupts the wall-clock numbers invisibly — the same failure the
one-experiment-at-a-time rule in `CLAUDE.md` exists to prevent. Launch through
`_spawn` (`start_new_session=True`) and tear down through `_reap` (SIGKILL to the
group).

## The monitor can see scoring

`retort monitor` finds in-flight work by looking for the **agent** process under
`retort run`. The probes have no agent — they launch the model's own program — so
for the whole scoring phase the monitor saw a live run with no recognizable child
and reported a working cell as *not started*. `scoring/probe_status.py` leaves a
breadcrumb keyed by the run pid, and the monitor renders the named phase
("measuring runtime (go)") where it would otherwise say "running". Stale
breadcrumbs from a crashed run are ignored rather than believed.

## Adding a language

`_build_then_entry(run_dir, language)` returns `(command, note)`. Rules, each
learned the hard way:

1. **Return absolute paths.** The command runs with `cwd=run_dir`; a relative
   `target/release/server` resolves against the wrong root, `Popen` raises
   `FileNotFoundError`, and the probe reports "server did not answer" — so every
   compiled language looked like a broken program when the binary was fine.
2. **Derive the entrypoint from the project's own manifest** — the binary name
   from `Cargo.toml`, the start command from `package.json`, the escript from
   `mix.exs`, the console script from `[project.scripts]`. Do not guess a
   convention. Python's package layout (`pkg/server.py` with relative imports)
   *cannot* be started as a path and must use `-m`.
3. **Install declared dependencies.** Running archived code against the system
   interpreter excluded every project that declared any, which was not a random
   subset. Python builds a venv cached by dep-set under the runtime root — never
   inside the archived run, which lives in the repo.
4. **The build is untimed** and runs once, before measurement. Charging a
   compiled language for `cargo build` inside a latency figure would describe the
   compiler, not the program. Build cost is already in `_duration_seconds`.
5. **No recipe → explicit non-result**, with a note. Not a zero.

## Adding a task

`detect_task(run_dir)` reads `TASK.md`. A task needs a probe that drives its
interface: `_probe_brazil` speaks MCP over stdio; `_probe_bookshop` is a stub
that returns a non-result, because it needs a per-language server launch and an
HTTP port handshake that does not exist yet.

## Protocol handshake — all three lines are load-bearing

`BRAZIL_CALLS` is `initialize` → `notifications/initialized` → `tools/list`.

- **Send them ONE AT A TIME, waiting for each reply.** This is the single
  biggest source of false failures found so far. The probe used to write all
  three in one burst and only then start reading; several implementations read
  stdin into a buffer, parse the first message in it, and drop the rest of the
  read. They answer `initialize` and then look dead. Measured on the same
  binaries: batched, C and Rust answer `[1]` and stall for 15 s; one-at-a-time,
  both answer `[1, 2]` in under 5 s. **No real MCP client pipelines the
  handshake**, so those servers were never broken — the probe was. Fixing this
  alone took the corpus from 30/53 to 43/53 measured and from 10 languages to
  all 13.
- **Capture stderr.** It used to go to `DEVNULL`, which discarded the only
  evidence of why a server failed to start: a Java `NoClassDefFoundError`, a
  Python `ModuleNotFoundError` and a genuinely hung Erlang server all produced
  the identical note, "server did not answer". Use a temp FILE, not a pipe —
  nothing drains a pipe while the handshake is in flight, so a chatty server
  would deadlock.
- `initialize` must carry `capabilities` **and** `clientInfo`. The TypeScript
  servers validate with zod and reject the handshake without them; omitting both
  produced a `-32603` that read as "the server never answered".
- `notifications/initialized` is **required, not decorative**. A spec-faithful
  server will not serve `tools/list` until it sees the notification, and sits
  silent — indistinguishable from a broken program.
- Read replies with a **timeout**. `proc.stdout.readline()` blocks forever, so a
  deadline loop wrapped around it is decorative; one Erlang server hung this
  probe for 25 hours. `_readline_timeout` uses `selectors`.
- Skip non-JSON lines: several implementations print a start-up banner first.

## `rows_loaded` is a result, not a caveat

Scraped from the server's own start-up banner. **Fewer rows can mean a better
implementation.** The five brazil match files overlap on purpose, so the same
fixture appears two or three times; 23,954 is exactly the sum of the five files
and therefore means *no deduplication*. One run reporting it answered
"Corinthians 2022 home: 44 matches" where the spec's worked example says 19.
Go's 16,947 comes from a competition-canonical ±1-day key and is correct.

## Do not measure on a busy machine

`measure()` refuses when an experiment is running, because wall-clock numbers
taken under contention are wrong in a way nothing in the archive records. The
inline path passes `allow_busy=True` — during its own run the machine is by
definition busy with that run, and the alternative is no data at all. Treat
inline numbers as comparable within an experiment; use `retort rebuild` on a
quiet machine for cross-experiment comparison.
