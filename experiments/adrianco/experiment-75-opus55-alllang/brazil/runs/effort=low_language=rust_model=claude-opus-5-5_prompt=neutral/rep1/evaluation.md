# Evaluation: effort=low_language=rust_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=claude-opus-5-5, effort=low, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 31 passed / 0 failed / 0 skipped (31 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests ran and passed)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

All requirements from the experiment's pinned `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/mcp.rs:116` `handle` (JSON-RPC initialize/tools list/call); 12 tools in `tool_definitions` (mcp.rs:38); stdio loop `src/main.rs:19` |
| R2 | Load & use datasets in data/kaggle/ | ✓ implemented | `src/data.rs:235` `Dataset::load` reads all 6 CSVs; `tests/bdd.rs:26` asserts 6 files with correct row counts (fifa 18207, novo 6886, BR-Football 10296) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/query.rs:115` `find_matches` with `venue` = home/away/either; `tests/bdd.rs:71` |
| R4 | Filter by date range and/or season | ✓ implemented | `MatchFilter.season`/`date_from`/`date_to` (query.rs:145); `tests/bdd.rs:116` date range, `:91` season |
| R5 | Filter by competition | ✓ implemented | `Competition` enum + `parse` (data.rs:27); filter query.rs:143; `tests/bdd.rs:99,125` Copa/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/query.rs:223` `team_record` / `:234` `team_stats_text`; `tests/bdd.rs:139,152` |
| R7 | Player search by name | ✓ implemented | `src/query.rs:434` `find_players` name substring; `tests/bdd.rs:270` neymar |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `find_players` nationality/club/position/min_overall (query.rs:434); ratings in `fmt_player` (query.rs:467); `tests/bdd.rs:261,279` |
| R9 | Season standings computed from matches | ✓ implemented | `src/query.rs:285` `standings` → `table` (points from wins/draws); `tests/bdd.rs:178` 2019 Flamengo 90 pts |
| R10 | Aggregate statistics | ✓ implemented | `league_stats_text` avg goals/home-away rates (query.rs:324), `biggest_wins_text` (:311), `rank_teams_text` (:361); `tests/bdd.rs:215,231` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query.rs:194` `head_to_head` / `:205` `head_to_head_text`; `tests/bdd.rs:86` |
| R12 | Automated tests covering queries | ✓ implemented | `tests/bdd.rs` — 31 BDD scenarios; `test_coverage=1.0` (all ran + passed) |

Enhancements beyond spec (not deductions): cross-file fixture de-duplication (`query.rs:64`), derbies tool, `rank_teams`, `team_competitions`, extended corner/shot/attack stats, champion + relegation-zone labelling, accent-folding team-name canonicalization with hand-tuned aliases, multi-format date parsing.

## Build & Test

Not re-run — stored mechanical scores were read from `scores.json` (per the evaluate-run skill; re-running the Rust toolchain is pure duplication).

```text
scores.json (this run)
  test_coverage   = 1.0     ⇒ cargo build + `cargo test` ran, all 31 tests passed
  code_quality    = 0.8333
  defect_rate     = 0.8432
  maintainability = 0.4623
  idiomatic       = 0.76
  token_efficiency= 0.0190
```

Skip/disabled scan: `grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]"` over `*.rs` → 0 matches. No skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,188 (src/*.rs) |
| Lines of code (incl. tests) | 1,513 |
| Files (source + tests) | 6 (.rs) |
| Dependencies | 2 (`csv`, `serde_json`) |
| Tests total | 31 |
| Tests effective | 31 |
| Skip ratio | 0% |
| Build duration | not re-run (read from scores.json) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Large single-file modules reduce maintainability (query.rs 537 LOC, data.rs 469 LOC; maintainability=0.4623)
2. [info] Cross-file fixture de-duplication across overlapping datasets (enhancement)
3. [info] Beyond-spec query tools: derbies, rank_teams, team_competitions, extended stats (enhancement)
4. [info] Low token efficiency for a low-effort cell (token_efficiency=0.0190)

No requirement gaps, build/test failures, or skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-75-opus55-alllang/brazil/runs/effort=low_language=rust_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                                             # stored mechanical scores (do not re-run toolchain)
grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" . --include="*.rs" # skip/disabled scan → 0
grep -cE "^\s*#\[test\]" tests/bdd.rs                        # 31 tests
wc -l src/*.rs tests/*.rs                                    # LOC
# Optional full re-run (slow, not required — scores already stored):
# cargo test
```
