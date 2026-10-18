# Evaluation: effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=clojure, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 49 deftests / 123 `is` assertions passed, 0 failed, 0 skipped (49 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json); build+tests succeeded
- **Lint:** pass — `code_quality=0.9167` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores from `scores.json` (inline gate; run not yet in retort.db): test_coverage=1.0, code_quality=0.9167, defect_rate=0.9283, maintainability=0.8368, idiomatic=0.80, token_efficiency=0.0069.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.clj` JSON-RPC 2.0 over stdio: initialize/ping/tools.list/tools.call; `tools.clj:tool-descriptors` registers 7 tools |
| R2 | Load & use datasets in data/kaggle/ | ✓ implemented | `data.clj:load-matches-from` reads all 6 CSVs; `data_test.clj:20` smoke-tests against the real Kaggle files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `queries.clj:filter-matches` + `venue-ok?`; `queries_test.clj:venue-filter-restricts-to-home-or-away` |
| R4 | Filter by date range and/or season | ✓ implemented | `filter-matches` `:season`/`:from`/`:to`; `queries_test.clj:search-matches-by-competition-season-and-dates` |
| R5 | Filter by competition | ✓ implemented | `filter-matches` `:competition` via `names/competition-key`; data spans Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `queries.clj:team-record`/`record`; `queries_test.clj:team-record-counts-results-and-goals` |
| R7 | Player search by name | ✓ implemented | `queries.clj:search-players` `:name`; tool `search_players` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `search-players` `:nationality`/`:club`, returns `:overall`; `brazilian-club-summary` groups Brazilian players by club |
| R9 | Season standings from match results | ✓ implemented | `queries.clj:standings` computes 3/1/0 pts from matches; not hardcoded |
| R10 | Aggregate stats | ✓ implemented | `queries.clj:league-stats` — goals/match, home/away/draw rates, biggest wins |
| R11 | Head-to-head between two teams | ✓ implemented | `queries.clj:head-to-head`; `server_test`/`queries_test` exercise it |
| R12 | Automated tests of query capabilities | ✓ implemented | 49 deftests across 6 namespaces; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json
test_coverage = 1.0   → build + all tests passed (test gate)
code_quality  = 0.9167
defect_rate   = 0.9283
```

Test suite (static): `test-runner` runs csv/json/names/data/queries/server namespaces and `System/exit`s non-zero on any failure. 49 `deftest`, 123 `is` assertions, 0 skips (the one "skipped" grep hit is the word in a `csv_test` description, not a disabled test).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 893 |
| Lines of code (tests) | 363 |
| Files (src + test) | 15 |
| Dependencies | 0 (deps.edn `:deps {}`) |
| Tests total (deftests) | 49 |
| Tests effective | 49 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; none reduce the score:

1. [info] E1 — No top-scorers tool (optional in spec; scorer data absent from CSVs)
2. [info] E2 — search_players shows overall/position/club, not detailed skill attributes (R8 satisfied by overall rating)
3. [info] E3 — Statistical analysis is single-scope, no cross-season trends (R10 satisfied)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                         # stored mechanical scores (do not re-run build/test)
cat ../../REQUIREMENTS.json             # pinned 12-requirement checklist
grep -rc deftest test/brazilian_soccer/*.clj
# To actually run (optional, not required by eval): clojure -M:test
```
