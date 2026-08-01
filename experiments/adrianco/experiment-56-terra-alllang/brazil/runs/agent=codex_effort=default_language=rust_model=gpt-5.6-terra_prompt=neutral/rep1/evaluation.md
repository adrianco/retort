# Evaluation: rust · codex · gpt-5.6-terra · prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json); log shows `Finished` + `test result: ok. 3 passed`
- **Lint:** pass — `cargo fmt --check` clean in agent log; `code_quality=0.7222`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Clean run. A compact (721 LOC) Rust workspace implementing an MCP JSON-RPC stdio server over the six provided Kaggle CSVs. Build and all tests pass; no requirement is missing; no tests are skipped or ignored.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/main.rs:108` main loop dispatches `initialize`/`tools/list`/`tools/call`; `tools()` at :105 defines 7 tools |
| R2 | Loads & uses data/kaggle/ datasets | ✓ implemented | `src/lib.rs:140` `load_from_dir` reads 5 match CSVs + `fifa_data.csv`; test `loads_all_provided_sources` (:561) asserts >20k matches, >18k players |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/lib.rs:337` `same_team(&m.home, t) || same_team(&m.away, t)`; `search_matches` tool |
| R4 | Filter by date range and/or season | ✓ implemented | `src/lib.rs:340-342` season + from/to bounds; `main.rs:22-24` season/date_from/date_to args |
| R5 | Filter by competition | ✓ implemented | `src/lib.rs:106` `same_competition` + per-file default comp (:144,157,170); `main.rs:20` competition arg |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/lib.rs:350` `team_record`; `team_statistics` tool `main.rs:27` returns record+points+win_rate |
| R7 | Player search by name | ✓ implemented | `src/lib.rs:488` name filter; `search_players` tool `main.rs:48` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/lib.rs:489-491` nationality/club filters; `Player.overall/potential` (:26-27) returned |
| R9 | Standings computed from match results | ✓ implemented | `src/lib.rs:429` `standings()` accumulates points from matches and sorts by pts/GD/GF |
| R10 | Aggregate stats (avg goals/match, home vs away…) | ✓ implemented | `src/main.rs:61` `competition_statistics`: goals_per_match, home_wins, draws |
| R11 | Head-to-head between two teams | ✓ implemented | `src/lib.rs:389` `head_to_head`; `head_to_head` tool `main.rs:37` |
| R12 | Automated tests of query capabilities | ✓ implemented | `src/lib.rs:515` 3 `#[test]` fns exercise normalize/record/H2H/load/query; `test_coverage=1.0` |

No prompt-factor requirements: `prompt=neutral` maps to the benchmark's neutral instruction; no additional `P*` checkable instructions beyond TASK.md.

## Build & Test

Scores read from `scores.json` (inline gate) — build/test **not** re-run per the skill.

```text
test_coverage   = 1.0     # build + all tests passed
code_quality    = 0.7222
defect_rate     = 0.6927
idiomatic       = 0.8
maintainability = 0.2690
token_efficiency= 0.0274
```

Corroborating evidence from `_agent_stdout.log` (`cargo fmt --check && cargo test`):

```text
   Compiling brazilian-soccer-mcp v0.1.0 ...
    Finished `release` profile [optimized] target(s) in 4.32s
running 3 tests
test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.72s
     Running unittests src/main.rs ... running 0 tests ... ok. 0 passed
   Doc-tests brazilian_soccer_mcp ... running 0 tests ... ok. 0 passed
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 721 (`lib.rs` 569 + `main.rs` 152) |
| Files (excl. target/data/.git) | 14 |
| Dependencies (Cargo.toml) | 6 (anyhow, chrono, csv, serde, serde_json, unicode-normalization) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | ~4.3s compile (from log) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] `ask` NL tool passes the team name as both name and club filter for player questions — `src/main.rs:96`
2. [low] Dead `_mapping` parameter on `load_matches` — `src/lib.rs:213`
3. [info] MCP protocol implemented by hand rather than via an SDK crate — `src/main.rs:108-152`
4. [info] All queries are linear scans over in-memory Vecs — `src/lib.rs:333-349,484-499`

None reach medium+ severity; this run has no requirement, build, test, or skip defects.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/brazil/runs/agent=codex_effort=default_language=rust_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                                    # stored mechanical scores (build/test gate)
grep -E "test result|Finished" _agent_stdout.log   # build + test evidence
grep -rnE "#\[ignore\]" src --include="*.rs" | wc -l   # skipped/ignored tests -> 0
grep -rnE "#\[test\]"   src --include="*.rs" | wc -l   # test count -> 3
# Optional full re-run (not required; scores already stored):
# cargo test
```
