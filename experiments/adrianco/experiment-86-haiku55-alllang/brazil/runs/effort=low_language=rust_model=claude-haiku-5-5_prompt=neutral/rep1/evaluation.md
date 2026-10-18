# Evaluation: effort=low language=rust model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=claude-haiku-5-5, effort=low, prompt=neutral (agent=unknown, framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 32 passed / 0 failed / 0 skipped (32 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.8333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

All stored mechanical scores: `test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.8333`, `idiomatic=0.8`, `maintainability=0.5216`, `token_efficiency=0.0191` (source: `scores.json`).

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/mcp.rs:21` handle_line (initialize/ping/tools/list/tools/call); `src/main.rs:45` serves over stdio; `tests/mcp_protocol.rs` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `src/data.rs:148` Dataset::load reads all 6 CSVs; `tests/bdd_queries.rs:170` scenario_all_six_files_are_loaded |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/query.rs:26` find_matches + `Match::involves` (`src/query.rs:51`); tool `search_matches` (`src/tools.rs:136`) |
| R4 | Filter by date range / season | ✓ implemented | `src/query.rs:33-35` season + date_from/date_to filters; `src/tools.rs:30-33` args |
| R5 | Filter by competition | ✓ implemented | `src/query.rs:32` competition filter; `Competition` enum (`src/data.rs:17`) spans Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/query.rs:109` team_stats → `Record` (`src/query.rs:69`); tool `team_stats` (`src/tools.rs:188`) |
| R7 | Player search by name | ✓ implemented | `src/query.rs:290` name substring (accent-folded); `tests/bdd_queries.rs:149` partial-match scenario |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `src/query.rs:291-292` nationality/club filters; output includes Overall/Potential (`src/tools.rs:296`) |
| R9 | Standings computed from matches | ✓ implemented | `src/query.rs:177` standings (3-1-0, sorted); `tests/bdd_queries.rs:66` asserts real 2019 table (Flamengo 90 pts) |
| R10 | Aggregate statistics | ✓ implemented | `src/query.rs:236` league_stats: avg goals, home/draw/away rates, biggest wins; tool `league_stats` (`src/tools.rs:253`) |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query.rs:139` head_to_head; tool `head_to_head` (`src/tools.rs:204`); `tests/bdd_queries.rs:88` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 32 tests pass (`test_coverage=1.0`); `tests/bdd_queries.rs`, `tests/mcp_protocol.rs`, unit tests in `data.rs`/`normalize.rs` |

Enhancements beyond spec: Série B/C competitions wired from the extended dataset; `dataset_info` tool; cross-source match deduplication; accent-insensitive search throughout.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
=> build + all tests passed
```

```text
Final test run (from _agent_stdout.log):
  unit tests (data.rs + normalize.rs): 9 passed
  tests/bdd_queries.rs:   12 passed; 0 failed; 0 ignored
  tests/mcp_protocol.rs:  11 passed; 0 failed; 0 ignored
  doctests:                0
  Total: 32 passed, 0 failed, 0 ignored
(2 bdd tests failed on an earlier iteration; the agent fixed them before completing.)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 1,855 |
| Source modules | 7 |
| Test files | 2 (+1 shared fixture) |
| Files (excl. build/data/git) | 23 |
| Dependencies | 2 (csv, serde_json) |
| Tests total | 32 |
| Tests effective | 32 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] ±1-day dedup heuristic could merge two genuine same-pair fixtures (`src/data.rs:306`)
2. [info] Competition coverage extends beyond spec to Série B/C (`src/data.rs:26`)
3. [info] Robust team-name normalization with ambiguous-club disambiguation (`src/normalize.rs:103`)
4. [info] biggest_wins capped at top 5 (`src/query.rs:259`)

No critical/high/medium findings. All 12 requirements implemented with passing tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=rust_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                               # stored mechanical scores (build/test/lint)
grep -rhE "^\s*#\[test\]" src tests | wc -l    # 32 tests
grep -rnE "#\[ignore\]|todo!|unimplemented!" src tests   # none → no skips/stubs
# Full build+test (optional, not required — scores.json already has results):
# cargo test
```
