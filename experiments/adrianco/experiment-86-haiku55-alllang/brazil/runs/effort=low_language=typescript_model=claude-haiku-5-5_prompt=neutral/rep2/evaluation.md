# Evaluation: effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 56 passed / 0 failed / 0 skipped (56 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.733` (scores.json); not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores from `scores.json` (run evaluated inline, not yet in retort.db):
`test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.733`, `maintainability=0.676`,
`idiomatic=0.80`, `token_efficiency=0.0114`. `test_coverage=1.0` ⇒ build succeeded and
all tests passed.

## Requirements

Pinned checklist from `../../REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/index.ts:7` StdioServerTransport; `src/tools.ts:40` `createServer`, 11 `registerTool` calls; `test/tools.test.ts:36` lists 11 tools over real MCP protocol |
| R2 | Loads/uses data/kaggle datasets | ✓ implemented | `src/loader.ts:226` `readFileSync` of all 6 CSVs; `test/loader.test.ts:16` asserts 18,207 players loaded, 6 sources |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:112-118` venue any/home/away; `src/tools.ts:43` `search_matches` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:106-110` season / seasonFrom / seasonTo / dateFrom / dateTo |
| R5 | Filter by competition (3 competitions) | ✓ implemented | `src/loader.ts:86-159` loads Brasileirão/Copa do Brasil/Libertadores; `src/queries.ts:100` competition filter |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:140` `teamRecord`; `src/tools.ts:81` `team_record`; `test/tools.test.ts:53` |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:319` `searchPlayers` name fold-match; `test/tools.test.ts:105` finds "Gabriel Jesus" |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/queries.ts:321-330` nationality/club/minOverall; returns `overall`; `test/tools.test.ts:94` |
| R9 | Standings computed from match results | ✓ implemented | `src/queries.ts:183` `standings` computes points; `test/loader.test.ts:34` 2019 Flamengo=90pts, played=38 |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:274` `leagueStats` (avg goals, home/away rates), `:296` `biggestWins`, `:218` `rankTeams` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:164` `headToHead`; `src/tools.ts:105` `head_to_head`; `test/tools.test.ts:62` |
| R12 | Automated tests covering queries | ✓ implemented | 56 tests across 6 files; `test_coverage=1.0`; `test/queries.test.ts` (21), `test/tools.test.ts` (14) exercise every capability |

No `prompt` factor beyond `neutral` (a generic instruction file), so no `P*` requirements.

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
# build+test signal (scores.json)
test_coverage = 1.0   # vitest run: build (tsc) + all 56 tests passed
defect_rate   = 1.0   # build+test succeeded
```

```text
# test command (for reference): npm test  ->  vitest run
# 6 test files, 56 it()/test() cases, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src only) | 1363 |
| Lines of code (tests) | 532 |
| Files (excl. node_modules/data/dist) | 29 |
| Dependencies (prod+dev) | 5 |
| Tests total | 56 |
| Tests effective | 56 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — none above info severity:

1. [info] Four tools beyond the required capabilities (rank_teams, club_summary, team_profile, dataset_info)
2. [info] Cross-file dedupe + source prioritization prevents double-counting in standings
3. [info] code_quality 0.73 / maintainability 0.68 — sub-1.0 but non-blocking

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel)/experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores
grep -rE "\.skip\(|xit\(|it\.todo\(" test/        # skip detection (none)
grep -rhoE "\b(it|test)\(" test/*.ts | wc -l      # 56 tests
# build+test (only if re-verifying): npm ci && npm test
```
