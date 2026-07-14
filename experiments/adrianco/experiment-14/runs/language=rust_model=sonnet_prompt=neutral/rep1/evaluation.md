# Evaluation: language=rust_model=sonnet_prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=sonnet, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — from test_coverage=1.0 (scores.json)
- **Build:** pass — not re-run (test_coverage=1.0 implies build + all tests passed)
- **Lint:** pass — code_quality=0.8333 (scores.json); 0 warnings re-derived
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low, 1 info)

Mechanical scores (from `scores.json`, not re-run): test_coverage=1.0, code_quality=0.833, defect_rate=0.935, maintainability=0.246, idiomatic=0.78, token_efficiency=0.011.

The prompt factor is `neutral` (prompts/neutral.md prescribes no methodology and adds no checkable instructions), so there are no `P*` requirements — TASK.md / REQUIREMENTS.json is the whole spec.

## Requirements

Pinned checklist from `experiment-14/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/main.rs:103` process_request handles initialize/tools/list/tools/call; `src/mcp.rs:52` 8 tool definitions |
| R2 | Load provided data/kaggle/ datasets | ✓ implemented | `src/data.rs:98-109` loads all 6 CSVs; confirmed files present in `data/kaggle/` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/tools.rs:41-59` checks home & away via `team_matches` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/tools.rs:70-90` season + date_from/date_to (date-range edge: see DQ1) |
| R5 | Filter by competition | ✓ implemented | `src/tools.rs:62-67`; competition labels span all datasets (data.rs) |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/tools.rs:120-225` team_stats with home/away split |
| R7 | Player search by name | ✓ implemented | `src/tools.rs:338-342` name filter over FIFA players |
| R8 | Players by nationality/club + ratings | ✓ implemented | `src/tools.rs:343-362` nationality/club/position/min_overall, sorted by overall |
| R9 | Season standings computed from matches | ✓ implemented | `src/tools.rs:408-513` builds table, points=W*3+D, sorts by pts/GD |
| R10 | Aggregate stats | ✓ implemented | `src/tools.rs:565` competition_stats (avg goals, home/away rates), 516 biggest_wins, 666 top_scoring_teams |
| R11 | Head-to-head between two teams | ✓ implemented | `src/tools.rs:228-322` head_to_head W/L/D + goals + recent meetings |
| R12 | Automated tests of query capabilities | ✓ implemented | 15 `#[test]` (data.rs:364-386, tools.rs:732-824); test_coverage=1.0 |

No requirements missing or partial. Enhancements beyond spec: extra tools `biggest_wins`, `competition_stats`, `top_scoring_teams`; team-name normalization stripping state suffixes (`data.rs:50`).

## Build & Test

Not re-run — mechanical scores read from `scores.json` per the evaluate-run skill (test_coverage=1.0 ⇒ `cargo build` + all tests passed).

```text
# would reproduce:
cargo test
# expected: 15 passed; 0 failed; 0 ignored  (3 in data.rs, 12 in tools.rs)
```

Skip scan: `grep -rE "#\[ignore\]" --include="*.rs"` → 0 skipped/ignored tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1692 (main 195, mcp 285, data 387, tools 825) |
| Files (non-artifact, excl. data) | 14 |
| Dependencies | 4 direct (serde, serde_json, csv, anyhow); 16 packages in Cargo.lock |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] DQ1 — Date-range filtering broken for DD/MM/YYYY historical dataset (`src/tools.rs:77-90`)
2. [medium] DQ2 — team_stats/head_to_head double-count overlapping 2012-2019 Brasileirão (`src/tools.rs:137-175, 243-289`)
3. [low] T1 — Tests assert on output substrings, not computed values (`src/tools.rs:732-824`)
4. [info] ARCH1 — MCP layer hand-rolled instead of an MCP SDK crate (`src/mcp.rs`)

## Reproduce

```bash
cd experiment-14/runs/language=rust_model=sonnet_prompt=neutral/rep1
cat scores.json                                            # mechanical scores (no re-run)
grep -rE "#\[ignore\]" --include="*.rs" . | wc -l          # skip scan -> 0
grep -rhE "^\s*#\[test\]" src/*.rs | wc -l                 # 15 tests
# optional full re-run: cargo test
```
