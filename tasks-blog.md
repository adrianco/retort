# The Tasks, and the Fastest Solution Recorded for Each

*Published 2026-07-30 · updated 2026-07-30 — Adrian Cockcroft*

What retort actually asks an agent to build, and — for each task — a summary of the fastest run that fully passed. "Fastest" here means the shortest `duration_seconds` among runs scoring `requirement_coverage == 1.0`, restricted to runs whose **agent log was archived**, since a record with no log can't be shown.

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
| **Result** | 12/12 requirements · 14 tests pass (6 existing + 8 new) · coverage 0.99 |

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

---

## The `python` vs `python3` stumble

All three record holders — two different vendors, three different models — ran `python`, got `command not found`, and retried with `python3`. It costs each of them a step.

It is worth noting because it is a property of *this machine* (macOS with no `python` shim) leaking into every measurement, and it is charged to the model as a turn. It's small and it's uniform, so it doesn't distort comparisons — but it is a reminder that a benchmark number always includes some of the bench.
