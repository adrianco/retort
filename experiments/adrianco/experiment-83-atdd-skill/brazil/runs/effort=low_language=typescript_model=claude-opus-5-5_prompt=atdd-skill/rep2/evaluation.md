# Evaluation: effort=low language=typescript model=claude-opus-5-5 prompt=atdd-skill · rep 2

## Summary

- **Factors:** language=typescript, model=claude-opus-5-5, prompt=atdd-skill, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Prompt instructions:** 2/2 followed (invoke `msec:atdd-build`; spec→DSL→driver→impl layering)
- **Tests:** 24 passed / 0 failed / 0 skipped (24 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `npm run build` (tsc) then `vitest run`, `test_coverage=1.0 ⇒ build+tests green` (not re-run)
- **Lint:** n/a — no linter configured; `code_quality=0.733` from `scores.json`
- **Architecture:** `run-summary` skill not available to this harness; see `_atdd_review.md` for the four-layer breakdown
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts:22` `new McpServer`, `StdioServerTransport`, 15 `registerTool` calls |
| R2 | Load & use the `data/kaggle/` datasets | ✓ implemented | `src/data.ts:56-96` reads all 6 CSVs (Brasileirão, Cup, Libertadores, novo, BR-Football, fifa_data) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:33-40` venue home/away/any; tool `search_matches` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:29-32` `from`/`to`/`season`; test `matches.spec.ts:33` |
| R5 | Filter by competition | ✓ implemented | `src/queries.ts:9-17` `competitionMatches` maps Brasileirão/Copa do Brasil/Libertadores |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/queries.ts:51-62` `recordFor`; tool `team_record`; test `teams.spec.ts:9` |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:155` name filter; test `players.spec.ts:9` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/queries.ts:156-170` nationality/club/position/minOverall; `players.spec.ts:13,19` |
| R9 | Season standings computed from matches | ✓ implemented | `src/queries.ts:84-101` `standings`; test `competitions.spec.ts:10` (Flamengo 90 pts) |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:111-123` `overview`/`biggestWins`; `competitions.spec.ts:33,39` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:71-82` `headToHead`; tool `head_to_head`; `teams.spec.ts:14` |
| R12 | Automated tests over the query capabilities | ✓ implemented | 24 tests in `acceptance/*.spec.ts`; `test_coverage=1.0` |

**Prompt-factor instructions (`prompts/atdd-skill.md`):**

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Invoke `msec:atdd-build` before writing code | ✓ followed | `_agent_stdout.log` first Skill call is `msec:atdd-build`; `_atdd_review.json` `skill_invoked:true`, `course_fetches:20` |
| P2 | Build spec → DSL → protocol driver → implementation | ✓ followed | specs `acceptance/*.spec.ts`, DSL `acceptance/dsl/soccerDsl.ts`, driver `acceptance/drivers/mcpDriver.ts` (sole MCP-aware layer), SUT `src/` |

## Build & Test

```text
npm test  ->  npm run build (tsc)  &&  vitest run
test_coverage = 1.0  (scores.json)  => build succeeded and all tests passed
```

Scores read from `scores.json` (inline gate output), not re-run per the evaluate-run skill:

```text
code_quality=0.733  token_efficiency=0.0133  test_coverage=1.0
defect_rate=1.0  maintainability=0.709  idiomatic=0.68  atdd_review=0.75
```

Skip/`.only` scan over `acceptance/`: 0 — no disabled or focused tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 519 (`src/`) + 318 (`acceptance/`) = 837 |
| Files (src+acceptance) | 10 |
| Dependencies | 7 (3 runtime: `@modelcontextprotocol/sdk`, `csv-parse`, `zod`) |
| Tests total | 24 |
| Tests effective | 24 |
| Skip ratio | 0% |
| Build duration | not re-run (gate `test_coverage=1.0`) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] Acceptance tests assert exact facts from the full real-world CSVs instead of owned fixtures (`competitions.spec.ts:11`, `teams.spec.ts:11`, `competitions.spec.ts:16`) — brittle to a dataset refresh; `SOCCER_DATA_DIR` hook exists but the driver doesn't use it.
2. [low] Test titled "rank teams by home record" actually requests the away ranking (`competitions.spec.ts:44-46`).
3. [low] Brasileirão matches de-duplicated by season+home+away key can merge distinct fixtures (`src/data.ts:82`); documented tradeoff.
4. [info] 15 MCP tools registered, beyond the spec's required categories (`src/server.ts`) — surplus capability, not a deduction.

No critical or high findings: the run builds, every acceptance test passes, and all 12 pinned requirements are implemented with the prompted ATDD structure intact.

## Reproduce

```bash
cd experiments/adrianco/experiment-83-atdd-skill/brazil/runs/effort=low_language=typescript_model=claude-opus-5-5_prompt=atdd-skill/rep2
cat scores.json                                   # stored mechanical scores (test_coverage=1.0)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(|\.only\(" acceptance --include="*.ts" | wc -l   # 0
# build+test (only if re-verifying; gate already ran it):  npm install && npm test
```
