# Evaluation: language=go · model=sonnet-5 · prompt=bdd · rep 1

## Summary

- **Factors:** language=go, model=sonnet-5, prompt=bdd (framework/agent unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 42 passed / 0 failed / 0 skipped (42 effective)
- **Build:** pass — compiled binary present; `defect_rate=1.0` from retort.db
- **Lint:** pass — `code_quality=1.0` from retort.db (agent reports `go vet`/`gofmt` clean)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores (from `scores.json` / `retort.db`, not re-run): `test_coverage=0.738`,
`code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.494`, `idiomatic=0.88`,
`token_efficiency=0.005`. `defect_rate=1.0` ⇒ build + tests passed;
`test_coverage=0.738` reflects 73.8% line coverage (tests executed).

## Requirements

Pinned checklist from `../../REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `mcp.go` JSON-RPC 2.0 stdio server; `main.go`; `tools.go:BuildToolRegistry` registers 10 tools |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `loader.go:LoadAll` reads all 6 CSVs; `data/kaggle/` present; no external APIs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `store.go:FilterMatches` team key; `search_matches` tool |
| R4 | Match query by date range and/or season | ✓ implemented | `search_matches` `season` filter (`store.go:94`); date-range supported internally but not exposed — see finding R4 (low) |
| R5 | Competition filter (Brasileirão/Copa do Brasil/Libertadores) | ✓ implemented | `loader.go` tags each source competition; `competitionMatches` substring filter |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `store.go:TeamRecord`; `team_record` tool |
| R7 | Player search by name | ✓ implemented | `store.go:filterPlayers` name; `search_players` tool |
| R8 | Players by nationality/club with ratings | ✓ implemented | `store.go:filterPlayers` nationality/club; `search_players`/`top_players` sort by Overall |
| R9 | Standings computed from match results | ✓ implemented | `store.go:Standings` (points/GD, relegation); `standings` tool |
| R10 | Aggregate statistics | ✓ implemented | `store.go:StatsSummary` (avg goals, home/away/draw rates), `BiggestWins`, `BestRecord` |
| R11 | Head-to-head between two teams | ✓ implemented | `store.go:HeadToHead`; `head_to_head` tool |
| R12 | Automated tests over query capabilities | ✓ implemented | 42 tests across 6 `*_test.go` files; `test_coverage=0.738 > 0` |

### Prompt factor (bdd) conformance

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Given/When/Then structure | ✓ | Given/When/Then comment markers in every `*_test.go` (168 occurrences) |
| P2 | Tests named after observable behaviours | ✓ | All 42 funcs `Test_Given<state>_When<action>_Then<outcome>` |
| P3 | One assertion / behaviour per scenario | ✓ | e.g. `store_test.go` scenarios assert single behaviours (points ordering, rate sums) |
| P4 | Descriptive test names | ✓ | e.g. `Test_GivenOverlappingBrasileiraoSources_WhenLoadingAll_ThenDuplicateFixturesAreRemoved` |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
retort.db: defect_rate=1.0   -> build + tests passed
retort.db: code_quality=1.0  -> lint/quality clean (agent: go vet + gofmt clean)
retort.db: test_coverage=0.738 -> tests executed, 73.8% line coverage
```

```text
Test inventory (grep of *_test.go):
  42 Test functions, 0 t.Skip / t.Skipf, 0 disabled tests
  Files: dateparse_test(5) loader_test(4) mcp_test(6) normalize_test(6) store_test(13) tools_test(8)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, 9 files) | 2097 |
| Lines of code (tests, 6 files) | 830 |
| Go source files | 15 |
| Dependencies (third-party) | 0 (stdlib only; `go.mod` has no requires) |
| Tests total | 42 |
| Tests effective | 42 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Full list in `findings.jsonl`:

1. [low] R4 — date-range match filtering implemented in `MatchFilter` but not exposed as a `search_matches` tool parameter (season is; requirement still met).
2. [info] Cross-source fixture deduplication prevents triple-counted standings/stats (enhancement).
3. [info] Team-name normalization distinguishes identity-bearing (Atlético-MG) from decorative (Palmeiras-SP) suffixes (enhancement).

No critical/high/medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiment-15-sonnet5/brazil/runs/language=go_model=sonnet-5_prompt=bdd/rep1"
# Stored scores (authoritative — not re-run here):
sqlite3 -readonly ../../retort.db \
  "SELECT metric_name, value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs \
   WHERE json_extract(run_config_json,'\$.language')='go' \
     AND json_extract(run_config_json,'\$.model')='sonnet-5' \
     AND json_extract(run_config_json,'\$.prompt')='bdd' AND replicate=1 \
     AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
# Test inventory:
grep -rhE "^func Test" *_test.go | wc -l          # 42
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
# Optional full re-run (builds too):
go test ./...
```
