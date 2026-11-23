# Evaluation: agent=codex_effort=low_language=rust_model=gpt-6.2-sol_prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.833, idiomatic=0.8 (scores.json); maintainability=0.397
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

Pinned checklist from `../../REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/lib.rs:74 serve()` JSON-RPC 2.0 handshake + `tools/list`/`tools/call`; e2e stdio test `tests/behavior.rs:278` |
| R2 | Loads provided datasets in data/kaggle | ✓ implemented | `src/data.rs:231 Graph::load` reads 6 CSVs via `csv::Reader`; `src/main.rs:8` defaults to `data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/query.rs:186-195` venue filter; tool `search_matches` |
| R4 | Filter by date range / season | ✓ implemented | `src/query.rs:159-203` start/end_date + season; test `tests/behavior.rs:32` |
| R5 | Filter by competition | ✓ implemented | `src/query.rs:174,196` competition filter across Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/query.rs:272 team_stats`; test `tests/behavior.rs:92` |
| R7 | Player search by name | ✓ implemented | `src/query.rs:240` name_key contains; test `tests/behavior.rs:146` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/query.rs:241-250`; test asserts nationality/club + overall |
| R9 | Season standings computed from matches | ✓ implemented | `src/query.rs:333 standings` points/table from scores; test `tests/behavior.rs:179` |
| R10 | Aggregate statistics | ✓ implemented | `src/query.rs:450 analysis` avg goals, rankings, biggest wins; test `tests/behavior.rs:240` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query.rs:308-309` opponent/opponent_wins; test `tests/behavior.rs:122` |
| R12 | Automated tests over query capabilities | ✓ implemented | `tests/behavior.rs` 10 tests; test_coverage=1.0 |

No enhancements counted as deductions; three are surfaced as info findings.

## Build & Test

Scores read from `scores.json` (inline gate output) — build/test not re-run per skill guidance.

```text
test_coverage = 1.0   ⇒ cargo build + cargo test succeeded, all tests passed
defect_rate   = 1.0   ⇒ build+test success
code_quality  = 0.833
idiomatic     = 0.8
maintainability = 0.397
token_efficiency = 0.0289
```

Skip scan: `grep -rE "#\[ignore\]" --include=*.rs` → 0 ignored/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~1259 (src/*.rs) |
| Lines of code (tests) | 332 (tests/behavior.rs) |
| Source files | 4 (+1 test file) |
| Dependencies | 3 (csv, serde, serde_json) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| MCP tools exposed | 7 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Dense single-expression logic lowers maintainability — `src/query.rs:152`, `src/data.rs:38` (maintainability=0.397)
2. [info] Cross-feed fixture de-duplication/merge — `src/data.rs:377`
3. [info] Computed standings with relegation + completeness guard — `src/query.rs:333`
4. [info] End-to-end MCP stdio handshake test — `tests/behavior.rs:278`

No requirement_missing / requirement_partial / build_failure / test_failure / skipped_test findings.

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/brazil-sol/runs/agent=codex_effort=low_language=rust_model=gpt-6.2-sol_prompt=neutral/rep1
cat scores.json                               # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json                    # pinned 12-requirement checklist
grep -rnE "#\[ignore\]" . --include="*.rs"     # skip/disabled-test scan (0)
# optional, slow: cargo test                   # re-runs build + 10 tests
```
