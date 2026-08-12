# Evaluation: agent=codex model=gpt-5.6-sol prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-sol, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R1 implemented with a medium SDK-compat caveat, see Findings)
- **Tests:** all passed / 0 failed / 0 skipped (effective = full suite; `test_coverage=0.94` from scores.json)
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.83` (scores.json)
- **Factual gate:** pass — `_factual.json` score=1.0 (2019 Série A: Flamengo 28W-6D-4L, all 20 clubs)
- **Architecture:** run-summary skill unavailable in this session; module map inlined below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.py:127 create_mcp_server` registers 12 tools + resource + prompt; `test_server.py:47` verifies registration (medium SDK-API caveat, see findings) |
| R2 | Load & use data/kaggle CSVs | ✓ implemented | `soccer_graph.py:232 _load` reads all 6 files; `test_soccer_graph.py:22` asserts exact row counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `soccer_graph.py:428 find_matches(team=…)` via `_matches_by_team` index |
| R4 | Filter by date range and/or season | ✓ implemented | `soccer_graph.py:448-463` start/end/season filters; `test_soccer_graph.py:65` |
| R5 | Filter by competition (3 comps) | ✓ implemented | `find_matches(competition=…)`; competitions Brasileirão/Copa do Brasil/Copa Libertadores loaded per source |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `soccer_graph.py:472 team_statistics`; `test_soccer_graph.py:82` consistency + 2022 Corinthians home=19 |
| R7 | Player search by name | ✓ implemented | `soccer_graph.py:534 search_players(name=…)`; `test_soccer_graph.py:105` Neymar |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `search_players(nationality=,club=,min_overall=)`; `test_soccer_graph.py:98` Brazil ≥80 sorted |
| R9 | Season standings from match results | ✓ implemented | `soccer_graph.py:558 standings`; `test_soccer_graph.py:90` 2019 champion Flamengo 90pts/38 |
| R10 | Aggregate stats (avg goals, biggest wins, home/away) | ✓ implemented | `aggregate_statistics:591`, `biggest_wins:608`; `test_soccer_graph.py:111` |
| R11 | Head-to-head between two teams | ✓ implemented | `soccer_graph.py:507 head_to_head`; `test_soccer_graph.py:75` Fla-Flu totals consistent |
| R12 | Automated tests covering queries | ✓ implemented | 18 test functions (+parametrized: 7 normalizations, 21 NL questions) across 2 files; `test_coverage=0.94` |

## Build & Test

Not re-run per evaluate-run policy — stored mechanical scores used as the build+test signal:

```text
scores.json: test_coverage=0.94, defect_rate=1.0, code_quality=0.833,
             idiomatic=0.8, factual_accuracy=1.0, runtime=0.728, token_efficiency=1.0
_factual.json: ok=true, score=1.0 (2019 Série A record + 20/20 clubs verified)
```

`test_coverage=0.94` ⇒ suite executed and passed with 94% line coverage; `defect_rate=1.0` ⇒ build+test succeeded. Zero skipped/xfail tests (`grep` over `test_*.py` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,091 (server 190, query_engine 220, soccer_graph 681) |
| Lines of code (tests) | 251 (test_server 64, test_soccer_graph 187) |
| Source files (.py) | 5 |
| Dependencies | 1 runtime (`mcp`), 1 test (`pytest`) |
| Tests total | 18 functions (~46 cases incl. parametrization) |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |
| Data files loaded | 6 / 6 CSVs |
| Runtime (steady median) | 272 ms; first query 1045 ms (`_runtime.json`) |

## Architecture (module map)

- `soccer_graph.py` — data layer. `SoccerGraph` loads 6 CSVs into normalized `Match`/`Player` dataclasses, deduplicates overlapping match sources on (date, competition, team keys, score) with ±1-day tolerance, and builds team/club indexes. Team-name normalization handles state suffixes, accents, and club aliases.
- `query_engine.py` — `QueryEngine.ask()`, a deterministic (no-LLM) NL router mapping question phrasings to graph operations (derby, standings, head-to-head, player, aggregate, ranking intents).
- `server.py` — MCP layer. 12 tool functions wrap graph calls; `create_mcp_server()` registers tools + a resource + a prompt. Degrades gracefully (`mcp=None`) when the SDK is absent so unit tests run without the transport.

## Findings

Full list in `findings.jsonl`:

1. [medium] MCP transport depends on a speculative SDK API (`from mcp.server import MCPServer`, `mcp>=2,<3`) that doesn't match the published 1.x SDK (`FastMCP`) — registration logic is correct and unit-tested against a mock, but live MCP startup is unverified.
2. [info] Standings/factual accuracy verified: 2019 Brasileirão computes Flamengo 90 pts / 38 played (factual gate 1.0).
3. [info] Cross-file deduplication correctly reconciles overlapping match CSVs, avoiding the ~24k-row double-count failure mode.

## Reproduce

```bash
cd "experiments/adrianco/experiment-58-sol/brazil/runs/agent=codex_effort=default_language=python_model=gpt-5.6-sol_prompt=neutral/rep2"
cat scores.json _factual.json _runtime.json        # stored mechanical scores (build/test not re-run)
grep -rE "pytest\.skip|xfail" test_*.py | wc -l     # 0 skips
# optional live suite: pip install -e '.[test]' && pytest -q
```
