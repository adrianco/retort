# Evaluation: agent=hermes-local language=go prompt=none · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=none
- **Status:** ok — builds, all tests pass, but two silent data-correctness defects
- **Requirements:** 10/12 implemented, 2 partial, 0 missing
- **Tests:** 25 passed / 0 failed / 0 skipped (25 effective)
- **Build:** pass (test_coverage=0.602, defect_rate=1.0 from scores.json — build + tests ran)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 2 high, 1 medium, 2 low)

All 12 pinned requirements have working, tested code paths, and the compiled
binary (`brazilian-soccer-mcp`) is present. The run is functionally complete but
carries a high-severity data-mapping bug that silently corrupts the away team on
the largest match dataset, and a case-sensitivity bug that returns wrong team
records. Neither is caught by the test suite because the tests use synthetic,
exact-case fixtures rather than the real CSVs.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `main.go:44` mcp.NewServer + `mcp.AddTool` for 7 tools, StdioTransport |
| R2 | Load provided data/kaggle datasets | ✓ implemented | `loader.go` reads all 6 CSVs; `main.go:31-41` wires them; all 6 files present |
| R3 | Match query by team (home/away/either) | ~ partial | `store.go:41 SearchMatches` (home+away index) works, but `loader.go:48` corrupts Brasileirão away team → state code |
| R4 | Filter by date range / season | ✓ implemented | `store.go:59-70`; tested `store_test.go:72,87` |
| R5 | Filter by competition | ✓ implemented | `store.go:56`; Competition set per loader; tested `store_test.go:57` |
| R6 | Team W/L/D + goals for/against | ~ partial | `store.go:79 TeamStats` tested (`store_test.go:102`) but case-sensitive classification (`store.go:101-107`) gives wrong records on case mismatch |
| R7 | Player search by name | ✓ implemented | `store.go:166-171`; tested `store_test.go:136` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `store.go:172-186` (nationality/club/position, sorted by Overall); tested `store_test.go:148,155` |
| R9 | Standings computed from matches | ✓ implemented | `store.go:190 CompetitionStandings` (3-pt rule); tested `store_test.go:169` |
| R10 | Aggregate statistics | ✓ implemented | `store.go:281 StatsAnalysis`, `store.go:237 BiggestWins`; tested `store_test.go:189,210` |
| R11 | Head-to-head between two teams | ✓ implemented | `store.go:121 HeadToHead`; tested `store_test.go:117` |
| R12 | Automated tests for query capabilities | ✓ implemented | 25 tests across `loader_test.go` + `store_test.go`; test_coverage=0.602 (>0) |

## Build & Test

Scores read from `scores.json` (mechanical scorers already ran — not re-run per skill guidance):

```text
code_quality      = 1.0      (lint pass)
test_coverage     = 0.602    (build + tests executed; 25/25 pass per _agent_stdout.log)
defect_rate       = 1.0      (build + test succeeded)
maintainability   = 0.629
idiomatic         = 0.4
token_efficiency  = 0.0225
```

```text
go test ./...  (per agent log)
25/25 PASS in 0.45s   (8 loader tests + 17 store tests)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,407 (main 219, loader 352, store 350, tools 397, models 89) |
| Test LOC | 486 (loader_test 171, store_test 315) |
| Files (excl. data/, summary/, binary) | 20 (incl. 3 empty stub dirs) |
| Dependencies (go.sum lines) | 20 (2 direct: go-sdk/mcp, jsonschema-go) |
| Tests total | 25 |
| Tests effective | 25 |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R3 — Brasileirão loader reads away team from the `away_team_state` column (`loader.go:48`): `row[4]` is the 2-letter state, not the away team (`row[3]`). All 4,180 away teams become state codes.
2. [high] R6 — `TeamStats` W/D/L classification is case-sensitive (`store.go:101-107`) while the lookup index is case-insensitive; any case mismatch counts every match as a loss.
3. [medium] Query inputs are not normalized for state suffix (`store.go:43,80`); a `"Palmeiras-SP"` query never matches the stored normalized `"Palmeiras"`.
4. [low] Human-readable formatters (`tools.go:352 FormatTextContent` et al.) are never called by the handlers — dead code.
5. [low] Empty package dirs `loader/ store/ tools/` left alongside the flat source files.

## Reproduce

```bash
cd "experiment-26-brazil-35b-60m/brazil/runs/agent=hermes-local_language=go_prompt=none/rep2"
cat scores.json                                    # mechanical scores (do not re-run toolchain)
head -1 data/kaggle/Brasileirao_Matches.csv        # confirms away_team=col3, away_team_state=col4
sed -n '2p' data/kaggle/Brasileirao_Matches.csv    # Palmeiras-SP,SP,Portuguesa-SP,SP,1,1,2012,1
# loader.go:48 uses row[4] (state) as AwayTeam -> bug
grep -rEn "t\.Skip" . --include="*.go" | wc -l      # 0 skipped tests
```
