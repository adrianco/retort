# Evaluation: language=go_model=sonnet_prompt=ATDD · rep 3

## Summary

- **Factors:** language=go, model=sonnet, prompt=ATDD (agent=unknown, framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Prompt (ATDD):** followed in spirit (black-box acceptance tests through the MCP protocol) but with two deviations — tests run against the full real dataset instead of an empty/seeded system, and there is no underlying unit TDD (P4, P5 partial)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — `test_coverage=0.77` from retort.db
- **Build:** pass (compiled; `defect_rate=1.0`, `test_coverage=0.77` — both from retort.db, not re-run)
- **Lint:** pass — `code_quality=1.0` from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 3 medium, 2 low, 1 info)

## Requirements

Pinned checklist from `experiment-13/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `main.go` (mcp-go ServeStdio), `internal/server/setup.go:RegisterTools` registers 6 tools |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `internal/data/loader.go:LoadAll` reads all 6 CSVs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `internal/tools/matches.go` team/home_team/away_team filters; `TestFindMatchesByBothTeams` |
| R4 | Match query by date range / season | ✓ implemented | `matches.go` date_from/date_to/season; `TestFindMatchesByTeamAndSeason` |
| R5 | Match query by competition | ✓ implemented | `matches.go:matchesCompetition`; `TestFindCupMatches` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `internal/tools/teams.go:GetTeamStatsTool`; `TestGetTeamStats` |
| R7 | Player search by name | ✓ implemented | `internal/tools/players.go` name filter; exercised via `find_players` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `players.go` nationality/club, returns overall/potential; `TestFindBrazilianPlayers`, `TestFindPlayersByClub` |
| R9 | Standings computed from matches | ✓ implemented | `internal/tools/standings.go` computes points; `TestGetStandings` |
| R10 | Aggregate statistics | ✓ implemented | `internal/tools/stats.go` avg_goals/biggest_wins/home+away; `TestBiggestWins`, `TestAvgGoals` |
| R11 | Head-to-head between two teams | ✓ implemented | `internal/tools/headtohead.go:GetHeadToHeadTool`; `TestGetHeadToHead` |
| R12 | Automated tests over query capabilities | ✓ implemented | `acceptance_test.go` (10 tests through MCP); `test_coverage=0.77` |

### Prompt-factor (ATDD) instructions

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Each requirement → executable acceptance test | ✓ implemented | 10 acceptance tests cover all 5 capability categories |
| P2 | Test only through public interface (MCP), no back doors | ✓ implemented | `acceptance_test.go` uses `mcptest.Server` + `Client().CallTool`; no internal access |
| P3 | Assert WHAT not HOW, domain language | ~ partial | Behavioral for find/h2h; stats/standings tests assert field presence + sort only (see F1) |
| P4 | Each scenario starts from an empty system, no shared data | ~ partial | Every test loads the full real `data/kaggle/` CSVs and asserts on real contents |
| P5 | Finer-grained unit TDD underneath | ~ partial | No unit-test files exist; only the acceptance suite |

## Build & Test

Build, test, and lint were **not re-run** — scores read from `experiment-13/retort.db` /
`scores.json` (per the evaluate-run skill; re-running compiled toolchains is pure duplication).

```text
test_coverage = 0.77   # build + tests executed and passed (>0 ⇒ test gate passed)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 1.0    # lint/quality gate
idiomatic     = 0.76
maintainability = 0.46
token_efficiency = 0.060   (_tokens=500612, _cost_usd=2.13, _turns=14)
```

Test inventory (static): 10 `Test*` functions in `acceptance_test.go`, 0 skips
(`grep -E "t\.Skip\(|t\.Skipf\("` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source, non-test) | 1404 |
| Lines of code (Go test) | 334 |
| Files (excl. data/, .git) | 19 |
| Direct dependencies | 2 (mcp-go, testify); 37 lines in go.sum |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build | pass (not re-run; defect_rate=1.0) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] P4 — Acceptance tests run against the full production dataset, not an empty/seeded system (`acceptance_test.go:18`)
2. [medium] P5 — No finer-grained unit TDD beneath the acceptance suite (only `acceptance_test.go`)
3. [medium] F1 — Stat/standings tests assert field presence, not computed correctness (`acceptance_test.go:142`, `:262`)
4. [low] F2 — `find_matches` silently ignores season passed as a string (`internal/tools/matches.go:62`)
5. [low] F3 — `matchesCompetition` conflates BR-Football tournaments / exact brasileirao match (`internal/data/loader.go`, `matches.go`)

## Reproduce

```bash
cd experiment-13/runs/language=go_model=sonnet_prompt=ATDD/rep3
cat scores.json                       # mechanical scores (build/test/lint already computed)
grep -rE "^func Test" acceptance_test.go | wc -l   # 10 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
find . -name "*_test.go"              # only acceptance_test.go (no unit tests)
# DB cross-check (read-only):
sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'\$.language')='go' AND json_extract(run_config_json,'\$.model')='sonnet' AND json_extract(run_config_json,'\$.prompt')='ATDD' AND replicate=3 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
```
