# Evaluation: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-6-astra, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective)
- **Build:** pass — stdlib-only, zero dependencies (`defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 5 info)

Scores read from `scores.json` (inline gate; no DB row): `test_coverage=0.93`, `defect_rate=1.0`, `code_quality=0.833`, `maintainability=0.574`, `idiomatic=0.68`, `token_efficiency=0.012`. Build/tests were **not** re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.py:104 MCPServer`, `TOOLS` (13 tools), JSON-RPC lifecycle `server.py:114-161` |
| R2 | Loads provided data/kaggle/ datasets | ✓ implemented | `soccer.py:131-178` reads all 6 CSVs; `test_all_six_sources_loaded_and_queryable` asserts exact row counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `soccer.py:289 search_matches` + `_select` venue/team filter (`soccer.py:270-273`) |
| R4 | Filter by date range and/or season | ✓ implemented | `_select` season + `date_from`/`date_to` (`soccer.py:259-281`); `test_2020_season_includes_matches_played_in_2021` |
| R5 | Filter by competition (3 comps) | ✓ implemented | `competition_name` (`soccer.py:83`), `_select` comp filter; datasets span Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `team_statistics` (`soccer.py:320`) via `_record` (`soccer.py:303-318`); `test_given_three_results...` |
| R7 | Player search by name | ✓ implemented | `search_players` name filter (`soccer.py:340,351`) |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `search_players` nationality/club/overall (`soccer.py:348-354`); returns overall/potential/attributes; `test_player_search_and_cross_file_graph` |
| R9 | Season standings computed from matches | ✓ implemented | `standings` (`soccer.py:358`, 3pts/win); `test_2019_standings...` (Flamengo 90 pts) |
| R10 | Aggregate statistics | ✓ implemented | `statistics` goals/match, home-win rate, biggest wins, rankings (`soccer.py:398`) |
| R11 | Head-to-head records | ✓ implemented | `head_to_head` (`soccer.py:331`); `test_given_three_results...` asserts symmetry |
| R12 | Automated tests covering queries | ✓ implemented | `test_soccer.py` 20 tests, `test_coverage=0.93` (>0) |

No requirement is missing or partial. Several capabilities exceed the spec (knowledge graph, dedup/provenance, derbies, season trends, cup brackets, zipapp build) — logged as `enhancement` (info) in findings, not deductions.

## Build & Test

Not re-run per skill policy — stored scores used as the build+test signal:

```text
scores.json: test_coverage=0.93  defect_rate=1.0  code_quality=0.833
=> build + all tests passed; 93% line coverage
```

```text
test_soccer.py: 20 test methods (FixtureTests x6, DatasetTests x9, ProtocolTests x5)
skip/xfail scan: 0
Includes real stdio-subprocess and zipapp end-to-end tests (server.py, build.py).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 975 (soccer 480, server 193, test 274, build 28) |
| Files (excl. data/logs/artifacts) | 6 source/config + TASK/spec |
| Dependencies | 0 (stdlib only) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Sample questions | 28 (≥20 required) |
| Data files loaded | 6/6 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] soccer.py packs complex logic into very dense one-liners (maintainability=0.57) — `soccer.py:373`
2. [info] test_coverage=0.93 — ~7% of lines uncovered (error/edge branches)
3. [info] Enhancement: knowledge-graph tool `graph_neighbors` — `soccer.py:445`
4. [info] Enhancement: cross-source dedup with provenance + conflict reporting — `soccer.py:148-178`
5. [info] Enhancement: derbies / season_trends / competition_bracket / data_status / zipapp build

## Reproduce

```bash
cd "experiments/adrianco/experiment-73-astra-hard-task/brazil/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json                       # stored build/test/quality scores (not re-run)
python -m unittest test_soccer -v     # 20 tests (optional re-verify)
grep -cE "def test_" test_soccer.py   # 20
```
