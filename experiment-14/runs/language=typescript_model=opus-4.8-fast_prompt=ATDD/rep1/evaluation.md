# Evaluation: language=typescript · model=opus-4.8-fast · prompt=ATDD · rep 1

## Summary

- **Factors:** language=typescript, model=opus-4.8-fast, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 34 passed / 0 failed / 0 skipped (34 effective) — from `test_coverage=1.0`
- **Build:** pass (`test_coverage=1.0` ⇒ tsc build + vitest ran green; not re-run)
- **Lint:** n/a — `code_quality=0.733` from scores.json (no separate linter configured)
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 5 info)

Scores read from `scores.json` (inline gate output) — not recomputed:
`test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.733`, `maintainability=0.650`, `idiomatic=0.77`, `token_efficiency=1.0`.

## Requirements

Checklist is the pinned `experiment-14/REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/server.ts:91` `createSoccerServer` registers 7 tools on `McpServer`; `src/index.ts:43` `StdioServerTransport` |
| R2 | Loads provided `data/kaggle/` CSVs | ✓ implemented | `src/data/loaders.ts:716` FILES table loads all 6 CSVs; `tests/acceptance/real-data.test.ts` loads the real files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/data/store.ts:938` `findMatches` team/homeTeam/awayTeam/opponent filters; `tests/acceptance/match-queries.test.ts` |
| R4 | Match query by date range / season | ✓ implemented | `store.ts:951-953` season + dateFrom/dateTo; tool schema `server.ts:117-119` |
| R5 | Match query by competition | ✓ implemented | `store.ts:950` competition filter; loaders tag Brasileirão/Copa do Brasil/Libertadores (`loaders.ts:571,595,617`) |
| R6 | Team record (W/L/D, goals for/against) | ✓ implemented | `store.ts:965` `teamRecord` → wins/draws/losses/goalsFor/goalsAgainst/points; `tests/acceptance/team-queries.test.ts` |
| R7 | Player search by name | ✓ implemented | `store.ts:1183` `findPlayers` name via `foldText().includes`; `tests/acceptance/player-queries.test.ts` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `store.ts:1191-1194` nationality/club/position/minOverall; returns overall/potential |
| R9 | Season standings computed from matches | ✓ implemented | `store.ts:1062` `standings` builds table (3/1/0 pts, GD tiebreak); `competition-queries.test.ts` asserts champion by GD |
| R10 | Aggregate statistics | ✓ implemented | `store.ts:1127` `competitionStatistics` avg goals/match, home/away win rate, biggest wins |
| R11 | Head-to-head records | ✓ implemented | `store.ts:1015` `headToHead`; `tests/acceptance/team-queries.test.ts` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 34 tests across 8 files; `test_coverage=1.0` (suite executed green) |

### Prompt conformance (ATDD)

The ATDD prompt was followed faithfully (recorded as info findings P1/P2, not deductions):
- Acceptance tests exercise the SUT **only** through the public MCP interface — `tests/acceptance/harness.ts:30` connects a real MCP `Client` to the real server over `InMemoryTransport`; no back-door into internals (only the DataStore is seeded, the system's "database").
- Each scenario is atomic and independent — `beforeEach` starts a fresh empty system (`competition-queries.test.ts:11`).
- Assertions speak the domain language ("calculates a league table … names the champion") rather than implementation mechanics.
- Finer-grained unit TDD sits underneath (`tests/unit/normalize.test.ts`, `tests/unit/loaders.test.ts`).

## Build & Test

Not re-run — stored scores used per skill policy.

```text
# build (tsc -p tsconfig.json)  — inferred pass from test_coverage=1.0
# test  (vitest run)            — 34 passed / 0 failed / 0 skipped
```

Skip scan (`grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(|describe\.skip|test\.skip" tests/`): **0 skips**.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src/*.ts) | 1,232 |
| Lines of code (tests/*.ts) | 718 |
| Source files | 6 |
| Total project files (excl. node_modules/.git/data) | 27 |
| Dependencies (deps + devDeps) | 7 (`@modelcontextprotocol/sdk`, `csv-parse`, `zod` + `@types/node`, `tsx`, `typescript`, `vitest`) |
| Tests total | 34 |
| Tests effective | 34 |
| Skip ratio | 0% |
| MCP tools exposed | 7 |

## Findings

Full list in `findings.jsonl`. None at medium or above.

1. [low] F1 — Player nationality/position filters use exact equality, not substring (`src/data/store.ts:1191,1193`)
2. [info] P1 — ATDD prompt followed: acceptance tests drive the system through MCP only (`tests/acceptance/harness.ts:30`)
3. [info] P2 — Unit TDD underpins the acceptance layer (`tests/unit/*.test.ts`)
4. [info] F2 — Index fully rebuilt on every `addMatch` (`src/data/store.ts:833`)
5. [info] F3 — Same-base-name clubs disambiguated only when ambiguity observed (`src/data/store.ts:893`)
6. [info] F4 — Top scorers (TASK §4) correctly omitted — not in pinned reqs, not inferable from data

## Reproduce

```bash
cd "experiment-14/runs/language=typescript_model=opus-4.8-fast_prompt=ATDD/rep1"
cat scores.json                      # test_coverage=1.0, code_quality=0.733, ...
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/ --include="*.ts"   # 0 skips
grep -rhoE "\b(it|test)\(" tests/ --include="*.ts" | wc -l                  # 34
# build/test were NOT re-run — scores read from scores.json per evaluate-run policy
```
