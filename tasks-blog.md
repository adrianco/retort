# The Tasks: What Gets Built, and How Differently a Run Can Pass

*Published 2026-07-30 · updated 2026-08-07 — Adrian Cockcroft*

What retort actually asks an agent to build, and — for each task — the fastest and the slowest run that fully passed. Both mean shortest/longest `duration_seconds` among runs scoring `requirement_coverage == 1.0`, restricted to runs whose **agent log was archived**, since a record with no log can't be shown.

The slow end is worth as much attention as the fast end. Nothing fails there: every run below scores a perfect 1.00. They just take between 4× and 61× longer to get there, and the reasons differ per task — over-engineering on one, the language itself on another, and a tool that costs time on the third.

Task definitions live in [`tasks/`](tasks/) and are indexed by [`tasks/registry.yaml`](tasks/registry.yaml). Three of the seven registered tasks have been run at scale; the other four (`react-dashboard`, `cli-data-pipeline`, `brazil-bench-neutral`, `funkygibbon-port`) are defined but have few or no scored runs.

> **A caveat on records.** Two faster runs exist in `master.db` but are not shown here: a 2.49-min brazil (exp-2) and a 0.71-min rest-api (exp-1). Both predate agent-log archiving *and* the mechanical gate — a sibling exp-2 "pass" carries `test_coverage=0.0`, which today fails automatically. They are not comparable to the runs below.

---

## 1. `rest-api-crud` — the routine task

**Source:** [`tasks/rest-api-crud/`](tasks/rest-api-crud/) · 712 runs · the "easy" task

Build a CRUD REST API for a books collection: `POST /books`, `GET /books` (with `?author=` filter), `GET/PUT/DELETE /books/{id}`, plus `GET /health`. Data in SQLite or the language's embedded equivalent, JSON responses with correct status codes, input validation, a README, and at least 3 tests. Scored in all 13 languages.

This is the workhorse. It's deliberately unremarkable — the point is that a competent stack should score 1.00 on it every time, so it measures *reliability*, not capability.

### Fastest logged pass — 44.5s

| | |
|---|---|
| **Stack** | Claude Fable 5, `effort=low`, python, prompt=neutral |
| **Experiment** | `adrianco/experiment-49-versions-cloud` rep2 |
| **Duration** | **44.5 s** · 7 turns · $0.86 · 105,745 tokens |
| **Result** | 12/12 requirements · 6 tests pass · coverage 0.98 |

The entire run, condensed:

```text
[Read]  TASK.md
[TEXT]  "I'll build a Flask + SQLite book API with tests."
[Write] app.py
[Write] test_app.py
[Write] README.md
[Write] requirements.txt
[Bash]  python3 -m venv venv && ./venv/bin/pip install -q flask pytest && ./venv/bin/python -m pytest -q
     -> ...... [100%] 6 passed in 0.19s
[TEXT]  "Done — all 6 tests pass."
```

One read, four writes, one verification command, done. No exploration, no iteration, no failed attempt. This is what the routine task looks like when a model simply knows the answer — and it's why the routine task no longer discriminates between frontier models on *reliability*, only on cost.

### Slowest logged pass — 45.6 min, for the same 1.00

| | |
|---|---|
| **Stack** | Claude Opus 5, `effort=max`, python, prompt=neutral |
| **Experiment** | `adrianco/experiment-55-terra-vs-opus5-effort-bookshop` rep2 |
| **Duration** | **45.6 min** (61×) · 210 turns · 256 tool calls · **$24.96** (29×) · 18,448,183 tokens (174×) |
| **Result** | 12/12 requirements · **104** tests · coverage 1.00 |

2,351 lines against Fable 5's 194. It built a seven-module package, linted itself with `ruff` unprompted, spawned a subagent, and ran **mutation testing** — on a books CRUD API. Every one of the judge's five findings is an `info` noting scope *beyond* the spec: a `PATCH` endpoint, filtering and pagination, a hand-written 304-line OpenAPI document, WAL journaling, NUL-byte validation. The task asked for five endpoints, a health check and at least three tests.

It is not slop — it scores *better* on maintainability (0.85 vs 0.27) and idiomaticity. But the gate cannot tell the two runs apart: both are 1.00. The full breakdown, including how much variance the thinking dial adds, is in [experiments-blog.md](experiments-blog.md).

---

## 2. `brazil-bench` — the hard task

**Source:** [`github://brazil-bench/benchmark-template`](https://github.com/brazil-bench/benchmark-template) · 284 runs

Build an MCP server over six real Kaggle CSVs of Brazilian football (23,954 matches across five files with three *different* schemas, plus 18,207 FIFA players). Twelve pinned requirements in [`REQUIREMENTS.json`](tasks/brazil-bench/REQUIREMENTS.json): match queries by team / date-range / competition / season, team W-D-L records, player search and filtering, season standings computed from results, aggregate statistics, head-to-head, and automated tests.

It is hard for reasons that have nothing to do with algorithms: team names carry state suffixes and accents (`São Paulo-SP` vs `Sao Paulo`), one file uses Portuguese column names and `DD/MM/YYYY` dates, and **the datasets overlap** — the same real-world match appears in two or three files.

### Fastest logged pass — 3 min 19 s

| | |
|---|---|
| **Stack** | GPT-5.6 Terra (codex), `effort=medium`, python, prompt=neutral |
| **Experiment** | `adrianco/experiment-55-terra-vs-opus5-effort-brazil` rep1 |
| **Duration** | **199.5 s** · 16 agent steps · $0.3165 · 339,649 tokens (291,840 cached) |
| **Result** | 12/12 requirements · 7 tests pass · coverage 0.85 |

Previous best in the modern harness was 5.67 min (Opus 5, clojure); the fastest previous *python* brazil pass was 5.02 min. This is a real step change, not a rounding difference.

**The run, condensed:**

```text
[CMD]  ls && sed -n '1,240p' TASK.md && rg --files          # read spec + repo
[CMD]  sed -n '241,520p' TASK.md ... head data/kaggle/*.csv  # read rest of spec + data shapes
[CMD]  sed -n '1,240p' prompts.txt; wc -l data/kaggle/*.csv  # count rows
[MSG]  "building a dependency-free MCP stdio server with an indexed CSV data
        layer and BDD-style tests"
[EDIT] README.md, brazilian_soccer_mcp.py, server.py, test_*.py   # ALL files, one patch

[CMD]  python -m pytest -q                    -> exit 127: command not found: python
[MSG]  "The environment provides python3 rather than python"
[CMD]  python3 -m pytest -q                   -> 7 FAILED
                                                 "Extra data: line 2 column 1"
[EDIT] brazilian_soccer_mcp.py                # fix the extended-file parser
[CMD]  python3 -m pytest -q && python3 server.py <<< '{jsonrpc initialize}...'
     -> 7 passed in 3.19s
     -> loaded 23954 matches and 18207 players
     -> top 2019: [Flamengo 38pl 90pts, Palmeiras 74, Santos 74]
     -> {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05", ...}}
[CMD]  python3 -c "Counter by source file"    # investigate dataset overlap
[EDIT] brazilian_soccer_mcp.py                # add standings source-dedup guard
[CMD]  python3 -m pytest -q && py_compile && git diff --stat
[MSG]  "all seven BDD-style tests pass, including the known 2019 Brasileirão
        standings result, and the MCP stdio handshake/tool call succeeds"
```

Sixteen steps, two real failures, both diagnosed and fixed. Not a lucky one-shot.

**What the solution looks like.** 342 lines across 3 files, **zero dependencies** — Python standard library only:

- `brazilian_soccer_mcp.py` (291 lines) — a `SoccerData` service plus the MCP layer.
- `server.py` (5 lines) — entrypoint, calls `serve()`.
- `test_brazilian_soccer_mcp.py` (46 lines) — 7 BDD-named tests.

**Was the Kaggle data really blended and loaded? Yes.** All six files, verified in-run: `loaded 23954 matches and 18207 players`, which is exactly `10296 + 4180 + 1337 + 1255 + 6886`. Five match files with three different row shapes are normalized into one frozen `Match` dataclass by a dispatching row-mapper:

| Kind | Files | Columns it reads |
|---|---|---|
| `standard` | Brasileirao, Copa do Brasil, Libertadores | `datetime`, `home_team`, `away_team`, `home_goal`, `season`, `round` |
| `extended` | BR-Football-Dataset | `date`, `home`, `away`, `tournament`, plus corners/shots kept in an `extras` dict |
| `historic` | novo_campeonato_brasileiro | `Data` (DD/MM/YYYY), `Equipe_mandante`, `Gols_mandante`, `Arena`, `Vencedor` |

Team names are matched through a `normalized()` function that strips accents, lowercases, and removes state suffixes via a regex listing all 27 Brazilian UFs plus South American country codes — so `São Paulo-SP` and `Sao Paulo` compare equal. Dates go through a multi-format `parse_date`. Both are direct answers to the spec's data-quality notes.

**What database backend? None.** There is no database and no graph store — no SQLite, no Neo4j, no networkx, no index of any kind. `SoccerData` holds `self.matches: list[Match]` and `self.players: list[dict]`, and every query is a **linear scan** over all 23,954 matches, re-filtered per call. The agent's own summary called it an "indexed CSV data layer"; that is not accurate — `defaultdict` is imported and never used. At this data size a scan is fast enough that nothing catches it.

**On "knowledge graph":** the spec's overview asks for "a knowledge graph interface for Brazilian soccer data", but its *Required Capabilities* section — which is what the pinned `REQUIREMENTS.json` was authored from — specifies query categories, not storage. The word "graph" appears **zero times** in `REQUIREMENTS.json`. So this solution scores 12/12 while containing no graph whatsoever: no nodes, no edges, no traversal. It is a flat table with filters. Every brazil run in this project has been graded the same way, so the comparison between runs is fair — but the checklist does not test the spec's headline framing.

**A defect the gate did not catch.** Because the source files overlap in coverage (BR-Football 2014–2023, Brasileirao_Matches 2012–2022, novo_campeonato 2003–2019) and `load()` concatenates without deduplication, the same real-world match is counted two or three times. The agent noticed this *partially* — it added a guard so `standings()` uses only the dedicated file, but only for Brasileirão and only for seasons 2003–2019, which is why the 2019 table it printed is historically correct (Flamengo, 38 played, 90 points).

Everything else still double-counts. The run's own MCP handshake demonstrates it:

```json
{"team": "Corinthians", "season": 2022, "venue": "home",
 "matches": 44, "wins": 28, "draws": 11, "losses": 5, "goals_for": 62}
```

A Brasileirão club plays **19 home league matches** a season; even adding home cup and Libertadores ties, ~25 is the ceiling. 44 is the league fixtures counted twice plus the cups. The spec's own worked example says Corinthians' 2022 home record is 19 matches, 11 W, 5 D, 3 L.

The tests do not catch this because they assert *accounting identities* — `matches == wins + draws + losses`, `points == wins*3 + draws` — which stay true when every match is double-counted. The judge flagged the overlap as **low/enhancement** and scoped it to `standings()` alone; it is broader than that, and it is a correctness defect in `team_statistics`, `head_to_head`, `search_matches` and `aggregate_statistics`.

*This is a finding about the task's checklist, not a retraction of the run.* The 3m19s and the 12/12 stand as measured. But "passes the pinned requirements" and "returns correct answers" are not the same thing, and here they diverge.

### Slowest logged pass — 64 minutes of Objective-C

| | |
|---|---|
| **Stack** | Claude Opus 5, objc, prompt=neutral |
| **Experiment** | `adrianco/experiment-46-opus5-brazil` rep1 |
| **Duration** | **64.0 min** · 175 turns · 174 tool calls · **$31.31** |
| **Result** | 12/12 requirements · coverage 1.00 · `code_quality` 1.00 |

A different failure mode entirely: this one isn't gold-plating, it's the **language**. Nine thousand lines of `.m` and `.h` — a hand-rolled CSV parser, match/player models, a query engine and an MCP server — because Objective-C offers no ecosystem to lean on here. The tool mix says it plainly: 59 Edits, 42 Writes, 54 Bash, and only **2 Reads**. It was not exploring. It was typing.

The cleanest way to see the cost is to hold the model and task fixed and vary only the language. Opus 5 ran all 13 on this task, and every one scored 1.00:

| | clojure | python | rust | swift | java | go | cpp | erlang | c | csharp | elixir | objc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **min** | 5.7 | 16.1 | 38.2 | 39.4 | 41.4 | 42.2 | 42.3 | 52.8 | 53.2 | 56.4 | 58.3 | **64.0** |
| **$** | 2.55 | 9.38 | 20.08 | 16.87 | 20.18 | 22.35 | 17.50 | 23.01 | 24.11 | 39.05 | 33.61 | **31.31** |

Same model, same spec, same 1.00 — an **11× spread in wall clock and 15× in cost**, decided entirely by the language. (TypeScript is omitted: it passed in 59.9 min but recorded `$0.00`, a telemetry gap, not a free run.) This is the single strongest illustration of retort's premise that the *stack* is the unit of measurement, not the model.

---

## 3. `py-catalog-reservations` — the modify-existing task

**Source:** [`tasks/py-catalog-reservations/`](tasks/py-catalog-reservations/) · 18 runs

The other two tasks build from an empty directory. This one ships a working 111-line `catalog/` package (models, store, loans, service facade) **and its existing test suite**, then asks for a *reservations* feature: reserve only when zero copies are available, FIFO ordering, automatic fulfilment when a copy is returned, cancellation, all exposed through the facade — without breaking the six tests that already pass (a `no_regression` gate).

Built for the **graphify tooling factor**: it needs comprehension of code the agent did not write.

### Fastest logged pass — 72.8s

| | |
|---|---|
| **Stack** | Claude Opus 4.8, `tooling=none`, python |
| **Experiment** | `adrianco/experiment-44-graphify-catalog` rep1 |
| **Duration** | **72.8 s** · 15 turns · $0.43 · 302,025 tokens |
| **Result** | 11/11 requirements · 14 tests pass (6 existing + 8 new) · coverage 0.99 |

```text
[Read] TASK.md
[Read] catalog/models.py, catalog/store.py, catalog/loans.py,
       catalog/service.py, tests/test_catalog.py, conftest.py   # read EVERYTHING first
[TEXT] "Now I'll implement the reservations capability."
[Edit]  catalog/models.py          # add the Reservation type
[Write] catalog/reservations.py    # new service
[Edit]  catalog/service.py  (×2)   # wire into the facade
[TEXT] "Now the tests for the new behavior:"
[Write] tests/test_reservations.py
[Bash] python -m pytest -q     -> command not found: python
[Bash] python3 -m pytest -q    -> .............. [100%] 14 passed in 0.01s
[TEXT] "All 14 tests pass — the 6 existing tests plus 8 new reservation tests."
```

Note the shape versus the greenfield task: **six reads before the first edit.** On a modify-existing task the agent front-loads comprehension, then edits surgically — `models.py` and `service.py` are edited, not rewritten. That difference is the whole reason this task exists.

### Slowest logged pass — 4.5 min, and free

| | |
|---|---|
| **Stack** | Qwen3-Coder-Next 80B **local** (Hermes + oMLX), `tooling=beads`, python |
| **Experiment** | `adrianco/experiment-45-graphify-local-catalog` rep1 |
| **Duration** | **4.5 min** (3.7×) · 1,000,059 tokens · **$0.00** |
| **Result** | 11/11 requirements · coverage 1.00 |

The third failure mode is not a failure at all. This run is 3.7× slower than the cloud record and costs **nothing** — it ran on a laptop. For a task you run once, $0.43 and 73 seconds wins; for one you run in a loop, the free option changes the arithmetic. It is the clearest case for reading the cost column next to the clock.

One pattern worth flagging inside this experiment: the three slowest passing runs are all `tooling=beads` (4.5, 4.3, 4.2 min), while every `none` and `graphify` run came in faster (2.6–3.3 min). That matches the README's factor analysis, where `beads` measurably *adds* cost. At n=3 per arm it is a consistent ordering rather than a proven effect — but it is the direction the tooling factor exists to detect.

---

## Cheapest passing configuration, per language, per task

Every row below scores `requirement_coverage = 1.00`. This is the cheapest stack *measured so far* that fully implements the spec in that language — not the only one that passes, and at n=1 for most codex cells.

| language | bookshop — stack | $ | min | brazil — stack | $ | min |
|---|---|---:|---:|---|---:|---:|
| typescript | Terra `default` | 0.22 | 1.8 | Terra `default` | **0.15** | 1.2 |
| rust | Terra `default` | 0.14 | 1.6 | Terra `default` | 0.37 | 3.3 |
| python | Luna `default` | **0.06** | 3.8 | Terra `high` | 0.31 | 4.1 |
| go | Luna `default` | 0.08 | 2.0 | Terra `low` | 0.39 | 3.5 |
| c | Terra `default` | 0.26 | 2.9 | Terra `default` | 0.40 | 4.5 |
| cpp | Terra `default` | 0.26 | 2.7 | Terra `default` | 0.33 | 5.4 |
| csharp | Terra `default` | 0.26 | 4.3 | Terra `default` | 1.36 | 11.6 |
| java | Terra `default` | 0.38 | 3.5 | Terra `default` | 0.49 | 5.0 |
| clojure | Terra `default` | 0.33 | 2.7 | Terra `default` | 0.57 | 6.9 |
| erlang | Terra `default` | 0.34 | 3.3 | Terra `default` | 0.49 | 4.6 |
| elixir | Terra `default` | 0.42 | 4.5 | Terra `default` | 0.67 | 6.1 |
| swift | Opus 4.8 `default` | 1.25 | 5.2 | Fable 5 `default` | 9.24 | 15.9 |
| objc | Opus 4.8 `default` | 1.52 | 5.5 | Fable 5 `default` | **13.30** | 23.5 |

Two things stand out. **A codex tier is cheapest in 11 of 13 languages on both tasks** — the Claude entries survive only for Swift and Objective-C, and only because Terra has never been run on them (their toolchain was broken on this host until 2026-08-01, so those two cells are a gap, not a verdict). And **the hard task costs remarkably little more than the easy one** on the cheap stacks: TypeScript is *cheaper* on brazil (\$0.15) than on bookshop (\$0.22), because the routine task's floor is dominated by fixed overhead rather than by the work.

The Apple pair is the outlier by two orders of magnitude — \$13.30 for Objective-C on brazil against \$0.15 for TypeScript. That gap is a language-and-model artifact, not a difficulty one: the same spec, the same judge.

## Runtime: what the produced programs actually cost to *run*

Build cost is not run cost. A `runtime` scorer starts the produced program and times a **fixed, retort-authored probe** against it — the same operation against every implementation, rather than the model's own test suite, whose duration mostly reflects how many tests it chose to write (on the same task, one model wrote 6 and another 104).

**All 53 archived brazil runs from four experiments, in all 13 languages**, measured on a quiet machine. Three numbers, because they answer different questions.

### Time to first real answer

Process launch through to a genuine `tools/call` — the tool and its arguments synthesized from each server's own advertised schema, since MCP does not pin tool names.

| language | n | fastest | by | slowest | by | spread |
|---|---:|---:|---|---:|---|---:|
| **c** | 2 | 29 ms | opus-5 | 37 ms | fable-5 | 1.3× |
| **cpp** | 3 | 142 ms | fable-5 | 391 ms | terra@default | 2.8× |
| **csharp** | 3 | 215 ms | terra@default | 1,151 ms | opus-5 | 5.4× |
| **objc** | 3 | 240 ms | opus-5 | 1,703 ms | terra@default | 7.1× |
| **go** | 11 | 277 ms | opus-5@low | 900 ms | opus-5@high | 3.2× |
| **swift** | 3 | 297 ms | fable-5 | 1,923 ms | terra@default | 6.5× |
| **rust** | 2 | 328 ms | terra@default | 426 ms | opus-5 | 1.3× |
| **python** | 11 | 344 ms | terra@high | 1,252 ms | opus-5@xhigh | 3.6× |
| **typescript** | 3 | 386 ms | terra@default | 479 ms | opus-5 | 1.2× |
| **java** | 2 | 424 ms | fable-5 | 889 ms | opus-5 | 2.1× |
| **elixir** | 3 | 509 ms | opus-5 | 4,220 ms | terra@default | 8.3× |
| **clojure** | 2 | 952 ms | terra@default | 1,242 ms | opus-5 | 1.3× |
| **erlang** | 3 | 1,349 ms | fable-5 | 2,651 ms | opus-5 | 2.0× |

Across the corpus, 29 ms to 4,220 ms. The **median within-language spread is 2.8×** — that is the implementation moving the number with the language held fixed, and in four languages it is larger than the gap between neighbouring languages.

**Start-up alone would rank these wrongly**, so it is not the headline. `tools/list` is protocol metadata: an implementation that parses all 42k rows at import answers it having done the work, one that streams lazily answers having done none. Two Python runs of the same model at different thinking levels make the point — the lazy one (`yield from csv.DictReader(...)`) starts in 41 ms and takes 461 ms to answer a real question; the eager one (`rows = list(csv.DictReader(...))`) starts in 1,109 ms and answers in 2 ms. Measured to first answer they are 2.2× apart; measured to start-up, 27× apart *in the opposite order*.

### Per-request latency: smaller numbers, far bigger spread

Start-up is paid once. Per-request is paid on every call, and it is where implementations differ most. Timed against an already-warm process, repeating one real query with the data in memory:

| language | n | fastest | by | slowest | by | spread |
|---|---:|---:|---|---:|---|---:|
| **go** | 11 | 0.072 ms | opus-5@medium | 58.900 ms | terra@max | 815× |
| **cpp** | 3 | 0.083 ms | opus-5 | 59.539 ms | terra@default | 717× |
| **c** | 2 | 0.113 ms | opus-5 | 3.372 ms | fable-5 | 30× |
| **swift** | 3 | 0.124 ms | opus-5 | 116.647 ms | terra@default | 941× |
| **rust** | 2 | 0.148 ms | opus-5 | 2.776 ms | terra@default | 19× |
| **objc** | 3 | 0.238 ms | opus-5 | 187.793 ms | terra@default | 789× |
| **typescript** | 3 | 0.300 ms | opus-5 | 8.756 ms | terra@default | 29× |
| **csharp** | 3 | 0.462 ms | opus-5 | 4.516 ms | fable-5 | 10× |
| **python** | 11 | 0.593 ms | opus-5@medium | 156.201 ms | terra@low | 264× |
| **erlang** | 3 | 0.851 ms | opus-5 | 164.230 ms | terra@default | 193× |
| **java** | 2 | 0.865 ms | fable-5 | 1.348 ms | opus-5 | 1.6× |
| **clojure** | 2 | 2.618 ms | opus-5 | 5.288 ms | terra@default | 2× |
| **elixir** | 3 | 6.826 ms | fable-5 | 300.080 ms | terra@default | 44× |

**Across the corpus: 0.072 ms to 300 ms — 4,150×.** The absolute numbers are three orders of magnitude below start-up and the spread is two orders of magnitude wider. Nine languages vary more between their own implementations here than the entire language ranking varies at start-up.

**And the pattern is not about languages.** Opus-5 produced the fastest per-request implementation in 11 of the 13 languages; Terra the slowest in 10. By model median: opus **0.544 ms**, fable **4.516 ms**, terra **55.666 ms** — a 102× gap between models whose *cold starts* are indistinguishable (371–425 ms). Two models write programs that boot the same and then answer queries a hundred times apart.

That is the design survey showing up in the milliseconds. Opus precomputed a lookup index in 22 of 23 runs; Terra in 11 of 21, and only at higher thinking levels:

| indexing | n | per-request median | cold-start median |
|---|---:|---:|---:|
| precomputed index | 37 | 1.099 ms | 377 ms |
| linear scan | 14 | 6.189 ms | 453 ms |

Note what is *absent* — the expected trade-off. Indexing is supposed to cost start-up to buy query speed, and here it costs nothing: the indexed runs start faster too. There is no tension to balance on this task; one group simply built the better program. Indexing accounts for about 5.6× of a 102× gap, so most of Terra's cost lies elsewhere, with re-parsing per call the obvious candidate.

### All three phases, together

| language | n | cold start | + first query | = first answer | per-request |
|---|---:|---:|---:|---:|---:|
| **c** | 3 | 29 ms | 2 ms | 33 ms | 1.742 ms |
| **cpp** | 3 | 245 ms | 1 ms | 245 ms | 0.686 ms |
| **csharp** | 3 | 295 ms | 9 ms | 305 ms | 0.891 ms |
| **swift** | 3 | 322 ms | 0 ms | 322 ms | 0.139 ms |
| **python** | 11 | 348 ms | 83 ms | 727 ms | 2.329 ms |
| **rust** | 2 | 375 ms | 2 ms | 377 ms | 1.462 ms |
| **go** | 11 | 377 ms | 4 ms | 381 ms | 2.534 ms |
| **java** | 3 | 420 ms | 10 ms | 657 ms | 1.107 ms |
| **typescript** | 3 | 473 ms | 6 ms | 479 ms | 5.023 ms |
| **clojure** | 2 | 1,081 ms | 16 ms | 1,097 ms | 3.953 ms |
| **objc** | 3 | 1,158 ms | 6 ms | 1,163 ms | 5.558 ms |
| **erlang** | 3 | 1,415 ms | 14 ms | 1,606 ms | 7.090 ms |
| **elixir** | 3 | 3,381 ms | 333 ms | 3,395 ms | 27.718 ms |

Medians per language. **Which column matters depends entirely on process lifetime, and the two disagree about who wins.** Elixir boots 116× slower than C, yet its median implementation serves requests faster than Go's. A CLI invoked per command should read the start-up column; a long-lived server answering a million queries should read the last one, and would be badly misled by the first.

One run in the set is unreproducible rather than slow, and it is worth naming: a Python implementation declares `mcp>=1.2` and imports `mcp.server.fastmcp`, which mcp 2.0 removed. It was correct when written and does not start today against an unpinned resolve. Open-ended dependency constraints make an archive perishable — the probe now retries with a capped major version to recover the measurement.

### Dedup: the requirement nobody wrote down

The five brazil match files overlap on purpose, so the same fixture appears in two or three of them. **23,954 is exactly the sum of the files** — that number means no deduplication at all, and the run reporting it double-counts: its own handshake answered *"Corinthians 2022 home: 44 matches"* where the spec's worked example says 19.

The Go implementation loaded **16,947** and is the correct one. It canonicalises competition names across files and merges fixtures within a one-day window, because "one source stores the local kick-off and another the UTC date". It is externally verifiable: it reports **8,404** Série A matches for 2003–2023 against **8,406** expected from real season sizes, and its own `dataset_info` tool reports no load failures.

Both scored 12/12. Deduplication is an *implicit* part of the task — you cannot compute a correct 2019 table without it — and the pinned checklist never asks, because it tests whether a capability exists and not whether its answers are right.

**Do not rank on the row count alone, in either direction.** An early version of the reference script keyed only on date and team names, and on that basis the *correct* Go implementation looked like a loader that had lost 17% of the corpus. A low count can be careful merging or a broken loader, and the two are indistinguishable without the dedup key that produced them.

The right test is a golden answer rather than a row count: 2019 Série A is a 20-team double round-robin, so **every club played exactly 38** and Flamengo took the title on 90 points. `played == 38` means merged, `~76` means double-counted, fewer means data dropped. That probe is written (`scripts/brazil_dedup_verdict.py`) but has not yet produced verdicts across the full set — it is slow against implementations that never answer, and the run was stopped. Scores are deliberately *not* adjusted by it; the point is to learn how often implementations get this right, which is the evidence for whether the checklist should test correctness at all.

## How differently the same task got built

Every run in this section scored **12/12**. The checklist tests whether a capability exists, not how it was built — so the design decisions behind these programs are invisible in every number retort records. That is worth looking at directly, because two runs of the same model at different thinking levels produced programs 27× apart in start-up that disagreed about whether the data needed deduplicating at all.

So all 53 archived brazil implementations were classified by reading their source along six axes: storage, loading strategy, indexing, deduplication, MCP SDK versus hand-rolled protocol, and layout ([`scripts/implementation_survey.py`](scripts/implementation_survey.py)). These are **heuristics over source text** — evidence, not proof. Read the distributions, not any single run's label.

### Unanimity where variety was expected

**All 53 runs kept everything in memory.** Not one used SQLite, DuckDB, or any embedded database — in any of the 13 languages, from any of the three models. The task guide describes a "knowledge graph", and most runs did not build an explicit graph either: the graph is an index plus joins at query time. When the corpus is 42k rows of CSV, every model independently concluded that a database would be overhead. That is a strong prior, held unanimously, and it is the kind of agreement that only shows up when you look at the code rather than the score.

### Opus decides the same way at every thinking level; Terra's choices depend on it

The only cells with graded thinking levels are exp-55 (Python and Go, five levels, two models), so that is where model and effort separate cleanly:

| choice | model | low | medium | high | xhigh | max |
|---|---|---|---|---|---|---|
| **indexing** | opus-5 | index | index | index | index | index |
| | terra | index/scan | index/scan | index | index | index |
| **dedup** | opus-5 | date-window | key-set | key-set | key-set | key-set |
| | terra | key-set/**none** | key-set/**none** | date-window/**none** | date-window/key-set | key-set |
| **protocol** | opus-5 | hand/sdk | sdk | hand/sdk | sdk | hand/sdk |
| | terra | hand-rolled | hand-rolled | hand-rolled | hand/sdk | hand/sdk |

**Opus-5 never skipped deduplication at any thinking level, and always precomputed an index.** Terra reaches the same choices, but only as effort rises: it scans instead of indexing at low and medium, skips dedup entirely somewhere in low through high, and does not reach for the MCP SDK until xhigh. Across the corpus the indexing gap is stark — opus precomputed an index in **22 of 23** runs, terra in **11 of 21**.

The pattern extends to the all-language experiment, where terra ran at default effort: **it skipped deduplication in 10 of 11 runs.** Its one-in-eleven dedup rate at default effort against zero skips for opus at any level is the single largest behavioural difference found between these models.

**Caveat, and it is a real one:** non-default thinking levels exist only in exp-55 (Python and Go), while `default` is exp-56 (all 13 languages). Any aggregate table of "choice by effort" therefore mixes effort with language and experiment. The decomposition above avoids that by staying inside one experiment, at the cost of **n = 2 per cell**. Treat the direction as the finding and the magnitude as provisional.

### The design choices are invisible at start-up and dominate per-request

Whether these decisions show up in the milliseconds depends entirely on which millisecond you look at:

| choice | n | median time to first answer | median per-request |
|---|---:|---:|---:|
| dedup: date-window | 14 | 351 ms | 2.236 ms |
| dedup: key-set | 25 | 509 ms | 1.333 ms |
| **dedup: none** | 12 | 412 ms | **63.324 ms** |
| indexing: precomputed | 37 | 479 ms | 1.099 ms |
| indexing: scan | 14 | 463 ms | 6.189 ms |
| protocol: SDK | 18 | 650 ms | 0.995 ms |
| protocol: hand-rolled | 33 | 426 ms | 5.288 ms |

In the first-answer column nothing separates: every gap is smaller than the within-language spread, and skipping deduplication even looks mildly *faster*, because there is less work to do at load. In the per-request column the same choices separate by 5–47×. **A run that never reconciled the overlapping files answers queries 28–47× slower than one that did** — it is scanning 23,954 rows where the others scan 17,000, on every single call, and the runs that skipped dedup are largely the same runs that skipped indexing.

So the correctness shortcut is also the performance shortcut, and both are invisible to the checklist that passed all of them.

Two caveats. These axes are confounded with language — C, C++ and Objective-C are hand-rolled in every run, TypeScript uses the SDK in every run — so "the SDK is 5× faster" is not a claim this data can make; the SDK runs are largely Opus's, and Opus indexed. And **the dedup labels could not be validated**: the plan was to check them against `rows_loaded`, since a run that skipped deduplication should report 23,954, exactly the sum of the five overlapping files, but that field is scraped from each server's start-up banner and is null for essentially every run here. The labels rest on source text alone.

The finding that survives all of it: these are 53 implementations of one specification, all of which passed, and they disagree about storage layout, when to load, whether to index, and whether the data needs reconciling at all. A pass-proportion sees none of it, and neither does start-up time.

## The `python` vs `python3` stumble — found here, since fixed

All three record holders — two different vendors, three different models — ran `python`, got `command not found`, and retried with `python3`. Each paid a step for it.

That is a property of *this machine* (macOS ships `python3` only) being charged to the model as agent work. Writing this page is what made it visible, because it is the one place three runs sit side by side.

Pulling the thread found two bigger problems behind it. **`pip install` was a coin flip:** against a Homebrew interpreter it fails with `externally-managed-environment`, so whether an agent could install a dependency at all came down to whether it happened to build a venv first — some did (Fable 5 above), some wrote stdlib-only code instead (Terra above). That is a difference in the *stack*, silently attributed to the model. And **the scorer built a different interpreter than the agent's**: it reuses a venv if the agent shipped one, otherwise it creates a throwaway — so a suite could be written against one interpreter and graded on another.

Retort now provisions a venv into every python workspace before the agent starts, with `python`, `pip` and pytest already on PATH, and the scorer reuses that same venv. Provisioning happens outside the timed window, so this removes a turn without adding time. Python runs from before and after this change are **not turn-count comparable** — it is logged in [experiments-blog.md](experiments-blog.md) with the other harness changes that moved numbers.

The general lesson is the one this project keeps relearning: a benchmark number always includes some of the bench.
