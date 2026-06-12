# Evaluation: language=clojure_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=clojure, model=sonnet, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (TASK.md, pinned `REQUIREMENTS.json`); prompt instruction P1 (ATDD) partially followed
- **Tests:** 23 test vars / 111 assertions passed / 0 failed / 0 skipped (23 effective) — `test_coverage=1.0`
- **Build:** pass — from `test_coverage=1.0` (`retort.db` / `scores.json`); not re-run
- **Lint:** pass — `code_quality=0.833` from `retort.db`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `core.clj:100` JSON-RPC 2.0 `initialize`/`tools/list`/`tools/call`; 6 schemas `core.clj:13` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data.clj:154 load-all-data` reads all 6 CSVs; `all-data-files-loaded` test asserts counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `tools.clj:43 team-in-match?`, `find-matches`; `find-matches-by-single-team` |
| R4 | Filter by date range / season | ✓ implemented | `tools.clj:57 date-in-range?`, season filter `tools.clj:76`; `find-matches-by-date-range` |
| R5 | Filter by competition | ✓ implemented | `tools.clj:21 competition-filter` (brasileirao/copa/libertadores); `find-matches-by-competition` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `tools.clj:102 get-team-stats`; `get-team-home-record` asserts W+D+L=played |
| R7 | Player search by name | ✓ implemented | `tools.clj:153 find-players` `:name`; `find-players-by-name` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `find-players` nationality/club/min-overall; `find-players-by-nationality`, `find-top-rated-players` |
| R9 | Standings calculated from matches | ✓ implemented | `tools.clj:240 compute-standings`; `get-brasileirao-standings` (Flamengo champ 2019) |
| R10 | Aggregate statistics | ✓ implemented | `tools.clj:283 get-statistics` (goals-per-match, biggest-wins, home-away, top-scoring) |
| R11 | Head-to-head between two teams | ✓ implemented | `tools.clj:190 get-head-to-head`; `get-head-to-head-record` |
| R12 | Automated tests of query capabilities | ✓ implemented | 23 deftest vars / 111 assertions; `test_coverage=1.0` |
| P1 | ATDD: tests through public MCP interface, empty/independent scenarios | ~ partial | acceptance tests present & domain-language, but call `tools/*` directly (not JSON-RPC `core/handle-request`) and share one preloaded full dataset (`acceptance_test.clj:18`) |

## Build & Test

Build/test not re-run — stored scores read from `experiment-14/retort.db` and `scores.json` (per skill: do not re-run the toolchain when scores exist).

```text
test_coverage = 1.0   ⇒ lein build + all tests passed
defect_rate   = 1.0   ⇒ build+test succeeded
code_quality  = 0.833
maintainability = 0.579   idiomatic = 0.67   token_efficiency = 0.0104
```

```text
Test inventory (static):
  test/brazilian_soccer_mcp/acceptance_test.clj — 20 deftest, ATDD acceptance suite
  test/brazilian_soccer_mcp/core_test.clj       —  3 deftest, normalize/data unit tests
  111 (is ...) assertions total; 0 skips / 0 #_ / 0 with-redefs disables
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test, .clj) | 1119 |
| Source modules | 4 |
| Test files | 2 |
| Dependencies | 3 (clojure, data.csv, cheshire) |
| Tests total (vars) | 23 |
| Tests effective | 23 |
| Assertions | 111 |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] P1 — ATDD acceptance tests bypass the MCP protocol public interface (call `tools/*` directly; `core/handle-request` untested)
2. [medium] P1b — Acceptance scenarios share a preloaded full dataset rather than starting empty/independent (contra the ATDD prompt)
3. [low] Q1 — Duplicate condition in `normalize-br-competition` (`data.clj:96`)
4. [info] E1 — Extra match statistics (corners/shots, multiple stat-types) beyond spec

## Reproduce

```bash
cd experiment-14/runs/language=clojure_model=sonnet_prompt=ATDD/rep1
cat scores.json   # stored mechanical scores (test_coverage=1.0, code_quality=0.833)
# DB cross-check:
sqlite3 -readonly ../../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id=(SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'$.language')='clojure'
      AND json_extract(er.run_config_json,'$.model')='sonnet'
      AND json_extract(er.run_config_json,'$.prompt')='ATDD'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
# Test inventory:
grep -rc '(deftest' brazilian-soccer-mcp/test/brazilian_soccer_mcp/*.clj
```
