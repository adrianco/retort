# Evaluation: language=rust · model=opus-4.8-fast · prompt=ATDD · rep 1

## Summary

- **Factors:** language=rust, model=opus-4.8-fast, prompt=ATDD (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (TASK.md) · 5/5 prompt (ATDD) instructions satisfied
- **Tests:** 23 passed / 0 failed / 0 skipped (23 effective) — 17 acceptance + 6 unit
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.83` (scores.json); no skip/ignore markers
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 2 info)

Mechanical scores read from `scores.json` (inline gate output) — build/test/lint
were **not** re-run. `test_coverage=1.0` ⇒ build succeeded and every test passed.
Other stored scores: `defect_rate=0.81`, `maintainability=0.54`, `idiomatic=0.85`,
`token_efficiency=0.0099`.

## Requirements

### TASK.md (pinned REQUIREMENTS.json)

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/mcp.rs` JSON-RPC 2.0, initialize/tools/list/tools/call, 7 tools registered |
| R2 | Loads & uses data/kaggle/ datasets | ✓ implemented | `src/data.rs:50` loads 5 match CSVs + `fifa_data.csv`; all 6 files present |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/tools.rs:79` search_matches team/home_team/away_team; `Match::involves` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/tools.rs:85-109` season + start_date/end_date filters |
| R5 | Filter by competition | ✓ implemented | `src/tools.rs:34` competition_ok; `normalize::canonical_competition_query` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/tools.rs:185` team_record; tested = Flamengo 2019 28-6-4, 90 pts |
| R7 | Player search by name | ✓ implemented | `src/tools.rs:326` search_players name filter |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/tools.rs:328-342` nationality/club/min_overall; returns overall/potential |
| R9 | Season standings from match results | ✓ implemented | `src/tools.rs:400` league_standings; tested = 20-team table, 38 played |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `src/tools.rs:505` competition_stats |
| R11 | Head-to-head between two teams | ✓ implemented | `src/tools.rs:263` head_to_head |
| R12 | Automated tests covering query capabilities | ✓ implemented | 17 acceptance + 6 unit tests; `test_coverage=1.0` |

### Prompt factor — ATDD (executable acceptance-test-driven, CD style)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Each requirement → executable acceptance test | ✓ implemented | `tests/acceptance.rs` covers all 6 capability categories (match/team/h2h/player/competition/stats) + cross-file query |
| P2 | External-user view; only via public MCP interface, no back-door | ✓ implemented | `tests/common/mod.rs:27` spawns the compiled binary, speaks JSON-RPC over stdio; zero access to internals |
| P3 | Assert WHAT not HOW, in domain language | ✓ implemented | test names/asserts e.g. `build_the_final_league_table_for_a_season`, `find_matches_between_two_specific_teams` |
| P4 | Atomic & independent scenarios | ✓ implemented | each test `McpClient::start()` = fresh process; no shared mutable state (see info finding on the literal "empty system" wording) |
| P5 | Finer-grained unit TDD underneath | ✓ implemented | unit tests for the trickiest internals: date parsing & competition canon (`normalize.rs`), alias/de-dup keys (`teams.rs`) — though thin (see low finding) |

No requirement is unmet. The ATDD discipline is genuinely followed: the
acceptance suite is true black-box (process boundary, MCP protocol only) and the
hardest correctness traps — accent folding, multi-format dates, and the
same-name-different-club merge problem — are pinned by unit tests.

## Build & Test

Not re-run — stored mechanical scores used (per skill policy).

```text
scores.json: test_coverage=1.0  → cargo build + cargo test: PASS (all tests)
             code_quality=0.83  → lint/quality
grep '#[ignore]' **/*.rs        → none (no skipped/disabled tests)
```

Test inventory (static count):
```text
tests/acceptance.rs : 17 #[test]  (black-box, over MCP)
src/normalize.rs    :  3 #[test]  (date/alias/competition canon)
src/teams.rs        :  3 #[test]  (key unification, distinctness, query match)
total               : 23 effective, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 2,227 |
| Source LOC (src/) | 1,668 |
| Test LOC (tests/) | 559 |
| Files (excl. target/.git) | 26 |
| Dependencies (Cargo.toml) | 4 (serde, serde_json, csv; +serde_json dev) |
| Tests total | 23 |
| Tests effective | 23 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] De-dup key omits round/stage — can merge distinct cup fixtures (`src/model.rs:53`)
2. [low] Team query falls back to substring containment, can over-match (`src/teams.rs:204`)
3. [low] Unit-TDD layer is thin relative to the ATDD prompt (data.rs/tools.rs have no unit tests)
4. [info] Acceptance tests run against the fixed corpus, not a per-test "empty system" (acceptable for a read-only query server)
5. [info] Date-range filter silently drops matches with no parseable date (`src/tools.rs:108`)

No critical or high-severity findings — the run builds, passes all tests, and
implements every requirement and prompt instruction.

## Reproduce

```bash
cd experiment-14/runs/language=rust_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json                                   # mechanical scores (no re-run)
grep -rnE "#\[ignore\]" . --include="*.rs"        # skipped/disabled tests: none
grep -cE '^\s*#\[test\]' tests/acceptance.rs       # 17 acceptance tests
# To verify locally (slow; not required):
SOCCER_DATA_DIR=data/kaggle cargo test
```
