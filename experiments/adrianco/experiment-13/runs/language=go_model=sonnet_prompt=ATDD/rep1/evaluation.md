# Evaluation: language=go_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=go, model=sonnet, prompt=ATDD
- **Status:** ok — builds and all tests pass (test_coverage=0.134, defect_rate=1.0 from retort.db); one high-severity correctness defect in aggregation
- **Requirements:** 11/12 implemented, 1 partial (R9), 0 missing
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — `go build` produced the `brazilian-soccer-mcp` binary (defect_rate=1.0; not re-run)
- **Lint:** pass — code_quality=1.0 from retort.db (not re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 2 low, 2 info)

## Requirements

Checklist is the pinned `experiment-13/REQUIREMENTS.json` (R1–R12), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `main.go:26-29` NewMCPServer+ServeStdio; `tools/tools.go:343` RegisterTools (6 tools) |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `soccer/loader.go:14-37` LoadStore reads all 6 CSVs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `soccer/store.go:21` FindMatches; AT01–AT03 |
| R4 | Filter by date range and/or season | ✓ implemented | `soccer/store.go:48` season filter; AT02. *No explicit date-range (low finding)* |
| R5 | Filter by competition (3 comps) | ✓ implemented | `soccer/store.go:42`; comps brasileirao/copa_brasil/libertadores; AT03 |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `soccer/store.go:86` GetTeamStats; AT04. *Counts inflated by R9 dedup gap* |
| R7 | Player search by name | ✓ implemented | `soccer/store.go:289` Name filter; `tools/tools.go:365` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `soccer/store.go:292-298`; `formatPlayer` tools.go:170; AT05, AT06 |
| R9 | Standings computed from matches | ~ partial | `soccer/store.go:126` GetStandings computes points, but double-counts overlapping brasileirão files (see Findings) |
| R10 | Aggregate stats (avg goals/biggest wins/home-away) | ✓ implemented | `soccer/store.go:318-388`; AT10, AT12. *goals_average inflated by R9 gap* |
| R11 | Head-to-head W/L/D between two teams | ✓ implemented | `soccer/store.go:231` GetHeadToHead; AT08 |
| R12 | Automated tests exercising queries; tests run | ✓ implemented | 17 tests, test_coverage=0.134>0, defect_rate=1.0. *Assertions weak — test-weak-1* |

**Prompt-factor (ATDD) conformance:** Acceptance suite AT01–AT12 (`acceptance_test.go`) is an executable spec driving the system through the MCP tool handlers (public interface), with finer-grained unit TDD underneath (`soccer/normalize_test.go`, `soccer/loader_test.go`) — good ATDD shape. **Gap:** the suite shares one package-global `testStore` loaded from the full production dataset in `TestMain`, so scenarios are not independent and do not "start from a running but empty system" as the prompt mandates (finding P4).

## Build & Test

Build/test were **not re-run** — scores read from `retort.db` / `scores.json` (per skill step 2):

```text
test_coverage = 0.134   # tests executed and passed (>0); 13.4% statement coverage
defect_rate   = 1.0     # go build + go test succeeded
code_quality  = 1.0     # lint/quality
maintainability = 0.490 | idiomatic = 0.58 | token_efficiency = 0.071
```

Test inventory (grepped, `acceptance_test.go` + `soccer/*_test.go`): 12 acceptance (AT01–AT12) + 5 unit (TestNormalizeTeamName, TestTeamsMatch, TestLoadStore, TestParseDate, TestParseGoals) = **17 tests, 0 skipped**.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of Go (total) | 1690 |
| Lines of Go (non-test source) | 1340 |
| Lines of Go (tests) | 350 |
| Go source files | 9 |
| Dependencies (modules) | 1 direct (`mark3labs/mcp-go`) + 3 indirect; go.sum 26 lines |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[high]** R9 — Brasileirão standings/team-stats double-count overlapping match files (`loader.go:155` & `loader.go:343` both tag `brasileirao`; 2019 = 380 rows in each file; no dedup → ~76 played / doubled points).
2. **[medium]** P4 — ATDD acceptance tests share a global pre-loaded store instead of an empty per-scenario system (`acceptance_test.go:14-23`).
3. **[medium]** test-weak-1 — Acceptance assertions only check substring presence, not computed values, so the R9 defect passes undetected (`acceptance_test.go:147-164`).
4. **[low]** R4 — Match filtering supports season but no explicit date range (`store.go:9`, `tools.go:344`).
5. **[low]** stat-default — `get_statistics` silently defaults unknown stat_type to goals_average (`tools.go:275-277`).

## Reproduce

```bash
cd experiment-13/runs/language=go_model=sonnet_prompt=ATDD/rep1
cat scores.json                                    # stored mechanical scores (no re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rnE "^func Test" acceptance_test.go soccer/*_test.go   # 17 tests
# verify brasileirão season overlap (root of R9):
awk -F, '$8==2019' data/kaggle/Brasileirao_Matches.csv | wc -l        # 380
awk -F, '$3==2019' data/kaggle/novo_campeonato_brasileiro.csv | wc -l # 380
```
