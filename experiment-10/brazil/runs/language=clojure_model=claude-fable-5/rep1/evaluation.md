# Evaluation: language=clojure_model=claude-fable-5 · rep 1

## Summary

- **Factors:** language=clojure, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 34 passed / 0 failed / 0 skipped (34 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.clj:1-120` JSON-RPC 2.0 over stdio; `tools.clj:246-349` 11 registered tools with inputSchema |
| R2 | Loads provided datasets from data/kaggle/ | ✓ implemented | `data.clj:210-290` load-brasileirao/cup/libertadores/historical/extended/players read all 6 CSVs |
| R3 | Match query: find by team (home, away, either) | ✓ implemented | `query.clj:35-41` team-pred; `query.clj:56-87` search-matches with :team filter checking both home/away |
| R4 | Match query: filter by date range and/or season | ✓ implemented | `query.clj:64-86` :season integer filter + :date-from/:date-to LocalDate range |
| R5 | Match query: filter by competition | ✓ implemented | `query.clj:49-54` competition-pred accent-insensitive substring; covers Brasileirão, Copa do Brasil, Libertadores |
| R6 | Team query: W/L/D record and goals for/against | ✓ implemented | `query.clj:117-151` team-record returns :wins/:draws/:losses/:goals-for/:goals-against/:win-rate |
| R7 | Player query: search by name | ✓ implemented | `query.clj:243-263` search-players :name filter on norm-name (accent-insensitive) |
| R8 | Player query: filter by nationality/club with ratings | ✓ implemented | `query.clj:243-263` :nationality/:club/:position/:min-overall filters; returns overall/potential/position |
| R9 | Competition query: season standings from match results | ✓ implemented | `query.clj:156-187` standings calculates 3-pts/win table from matches, sorted by points/wins/GD |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `query.clj:192-223` competition-stats (avg goals, home/draw/away rates); `query.clj:192-202` biggest-wins |
| R11 | Head-to-head records between two teams | ✓ implemented | `query.clj:92-112` head-to-head returns all meetings + W/D/L + goals from team1's perspective |
| R12 | Automated tests covering query capabilities | ✓ implemented | 4 test files, 34 deftests; test_coverage=1.0 (all pass); `tools_test.clj:62-109` exercises 23 sample questions |

## Build & Test

```text
Build + test gate: test_coverage=1.0, defect_rate=1.0 from scores.json
(build and tests not re-run per evaluate-run policy — stored scores used)
```

```text
Test files:
  data_test.clj     7 deftests — CSV loading, dates, normalization, dedup, UTF-8
  query_test.clj   13 deftests — match search, team stats, standings, players, head-to-head
  server_test.clj   8 deftests — MCP handshake, tools/list, tools/call, error codes, full session
  tools_test.clj    6 deftests — registry, formatted answers, error handling, 23 sample Qs, performance
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,171 |
| Lines of code (tests only) | 512 |
| Lines of code (total) | 1,683 |
| Files (excluding data) | 18 |
| Files (total) | 24 |
| Dependencies | 4 (clojure 1.12.0, data.csv 1.1.0, data.json 2.5.1, test-runner) |
| Tests total | 34 |
| Tests effective | 34 |
| Skip ratio | 0% |
| Stored scores | test_coverage=1.0, code_quality=0.833, defect_rate=1.0, maintainability=0.769, idiomatic=0.78 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] 11 MCP tools exposed, exceeding the 5 required capability categories
2. [info] Comprehensive team-name normalization across 5 match CSV files
3. [info] Cross-file match de-duplication with source-priority ranking
4. [info] BDD test suite with 34 tests and historical anchors for verification

## Reproduce

```bash
cd experiment-10/brazil/runs/language=clojure_model=claude-fable-5/rep1
cat scores.json
cat stack.json
grep -c "deftest" test/brazilian_soccer/*.clj
wc -l src/brazilian_soccer/*.clj test/brazilian_soccer/*.clj
find . -type f | wc -l
```
