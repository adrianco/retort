# Evaluation: language=clojure_model=opus-4.8-fast_prompt=ATDD · rep 1

## Summary

- **Factors:** language=clojure, model=opus-4.8-fast, prompt=ATDD (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ 4/4 ATDD prompt instructions satisfied)
- **Tests:** 20 deftests / 76 assertions — all passed, 0 failed, 0 skipped (20 effective)
- **Build:** pass — from `test_coverage=1.0` in retort.db/scores.json (build + tests ran clean; not re-run)
- **Lint:** n/a — `code_quality=0.833` from scores.json (no separate linter re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Pinned checklist from `experiment-14/REQUIREMENTS.json` (constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/soccer/server.clj` JSON-RPC 2.0 initialize/tools-list/tools-call; 6 tools in `tools.clj:tools` |
| R2 | Loads provided data/kaggle datasets | ✓ implemented | `src/soccer/data.clj:load-dataset` reads all CSVs; `real_data_test.clj` runs against `data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `query.clj:find-matches` → `filter-matches`/`involves?` |
| R4 | Match query by date range / season | ✓ implemented | `query.clj:filter-matches` season/start-date/end-date filters; `find-matches-a-team-played-in-a-season` test |
| R5 | Match query by competition | ✓ implemented | `filter-matches` competition filter; loads Brasileirão/Copa do Brasil/Libertadores; `find-matches-can-be-restricted-by-competition` test |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `query.clj:team-stats`; `team-home-record-for-a-season` test |
| R7 | Player search by name | ✓ implemented | `query.clj:search-players` name filter; `find-a-player-by-name` test |
| R8 | Players by nationality/club with ratings | ✓ implemented | `search-players` nationality/club filters, sorted by `:overall`; `find-brazilian-players` test |
| R9 | Standings calculated from match results | ✓ implemented | `query.clj:standings-rows`/`competition-standings` compute points; `league-champion-from-calculated-standings` test |
| R10 | Aggregate statistics | ✓ implemented | `query.clj:competition-stats` avg goals/match, home/away rate, biggest wins; `aggregate-competition-statistics` test |
| R11 | Head-to-head between two teams | ✓ implemented | `query.clj:compare-teams`; `compare-two-teams-head-to-head` test |
| R12 | Automated tests covering queries | ✓ implemented | 20 deftests across 4 files; `test_coverage=1.0` |

### ATDD prompt instructions (prompt factor = ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests exercise SUT only through public MCP interface, no back-door | ✓ | `test_helpers.clj:rpc` goes through `server/process-line`; `acceptance_test.clj` uses only `call-tool`/`list-tools` |
| P2 | Assert WHAT not HOW, in domain language | ✓ | Assertions on answer text / head-to-head / standings, not internals (`acceptance_test.clj`) |
| P3 | Atomic & independent, each starts from running-but-empty system | ✓ | `fresh-server` builds a private temp dataset per test (`test_helpers.clj:make-fixture-dir!`); real-data suite is separate coverage (info finding) |
| P4 | Executable acceptance suite drives the work | ✓ | `acceptance_test.clj` is an executable spec over the protocol; unit layer in `data_test.clj` |

No requirements missing or partial; one enhancement beyond spec (head-to-head folded into `find_matches`).

## Build & Test

Build/test not re-run — stored mechanical scores used per skill policy.

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.833
             maintainability=0.843  idiomatic=0.88  token_efficiency=0.0072
=> build + 20 deftests (76 assertions) passed; 0 failed; 0 skipped.
```

Test layout:
```text
test/soccer/acceptance_test.clj  13 deftests — MCP protocol acceptance spec
test/soccer/data_test.clj         6 deftests — normalization unit TDD
test/soccer/real_data_test.clj    1 deftest  — real data/kaggle coverage
```

Skip scan (`grep -rE "skip|disabled|TODO|FIXME|comment" src test`): none found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src) | 690 |
| Lines of code (test) | 377 |
| Source files (.clj) | 4 src + 4 test |
| Dependencies | 4 (clojure, data.csv, data.json, test-runner) |
| Tests total | 20 deftests / 76 assertions |
| Tests effective | 20 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Queries are linear scans over the full in-memory dataset with no indexing — fine for the spec's sizes/latency targets (`query.clj:filter-matches`).
2. [info] `find_matches` also emits head-to-head when team+opponent given — enhancement beyond R3 (`query.clj:96-110`).
3. [info] `real_data_test` reuses the shared `data/kaggle` dir rather than an isolated empty system — acceptable real-data coverage; the acceptance suite proper uses per-test fixtures (`real_data_test.clj:12`).

No critical, high, or medium findings. Conformance gate passed: full spec implemented and the test gate is green.

## Reproduce

```bash
cd experiment-14/runs/language=clojure_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json                 # stored mechanical scores (test_coverage=1.0)
grep -rhE "^\(deftest" test/ | wc -l        # 20 deftests
grep -rnE "skip|disabled|TODO|FIXME" src test # skip scan -> none
# full toolchain (only if re-verifying): clojure -X:test
```
