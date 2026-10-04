# Evaluation: effort=low language=typescript model=claude-opus-5-5 prompt=atdd-skill · rep 1

## Summary

- **Factors:** language=typescript, model=claude-opus-5-5, prompt=atdd-skill, effort=low (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`) · prompt P1 (ATDD workflow) followed
- **Tests:** 24 passed / 0 failed / 0 skipped (24 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `tsc`/vitest succeeded (`test_coverage=1.0`, `defect_rate=1.0`)
- **Lint:** n/a — no linter configured; `code_quality=0.733`, `idiomatic=0.65` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

Pinned checklist from `brazil/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/server.ts:createServer` registers 14 tools; `src/index.ts` connects `StdioServerTransport` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `src/data.ts:loadDataset` reads all 6 CSVs via `csv-parse`; `dataset_info` reports row counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:filterMatches` venue `home\|away\|all`; `search_matches` tool |
| R4 | Filter by date range / season | ✓ implemented | `src/queries.ts:filterMatches` `season`, `from`, `to`; spec test "matches by date range" |
| R5 | Filter by competition | ✓ implemented | `src/queries.ts:competitionName` maps Brasileirão/Copa do Brasil/Libertadores/Serie B/C |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/queries.ts:teamRecord` + `records()`; `team_record` tool |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:searchPlayers` name filter; `search_players` tool |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/queries.ts:searchPlayers` nationality/club/position + overall/potential |
| R9 | Standings calculated from results | ✓ implemented | `src/queries.ts:table`/`standings` compute points from `ds.league` matches |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:competitionStats`, `biggestWins`, `bestRecord`, `compareSeasons` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:headToHead` + `headToHeadSummary`; `head_to_head` tool |
| R12 | Automated tests covering queries | ✓ implemented | 24 acceptance tests in `test/acceptance/soccer-knowledge.spec.ts`; `test_coverage=1.0` |

**Prompt factor (P1 — `prompts/atdd-skill.md`):** Follow Dave Farley's ATDD (spec → DSL → protocol driver → implementation). ✓ followed — clean four-layer separation: domain-language spec (`test/acceptance/soccer-knowledge.spec.ts`, no MCP/CSV/JSON leakage), DSL (`test/dsl/SoccerDsl.ts`), protocol driver as the only MCP/stdio-aware layer (`test/drivers/McpSoccerDriver.ts`) driving the real server through its public interface. `_atdd_review.json`: `skill_invoked=true`, `acceptance_tests_found=true`, 21 course fetches, score 0.75.

## Build & Test

Scores read from `scores.json` (inline gate during `retort run`) — build/test **not** re-run per the skill.

```text
scores.json
test_coverage = 1.0   (build + all tests passed)
defect_rate   = 1.0   (build+test succeeded)
code_quality  = 0.733
maintainability = 0.857
idiomatic     = 0.65
atdd_review   = 0.75
token_efficiency = 0.0102
```

```text
skip scan (grep .skip/xit/xdescribe/it.todo/.only over src+test): 0
it(...) cases: 24  → 24 effective tests, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 499 (src) + 288 (test) = 787 |
| Files (src+test+docs) | 9 |
| Dependencies | 7 (3 runtime, 4 dev) |
| Tests total | 24 |
| Tests effective | 24 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; cached scores) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] `resolveTeam` bidirectional substring matching can over-match short names — `src/queries.ts:26`
2. [low] Performance specs assert on real wall-clock elapsed time (flake risk under load) — `test/drivers/McpSoccerDriver.ts:68`
3. [info] A spec expectation was changed to match the data (Ederson as top Brazilian GK) — `docs/atdd-findings.md:4`
4. [info] ATDD review scored 0.75 with some lower per-criterion grades — `_atdd_review.json`
5. [info] Analytics tools provided beyond required capabilities (enhancement) — `src/server.ts`

No critical/high/medium findings: the run fully implements the pinned spec and all 24 acceptance tests pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-83-atdd-skill/brazil/runs/effort=low_language=typescript_model=claude-opus-5-5_prompt=atdd-skill/rep1"
cat scores.json                                   # cached mechanical scores (test_coverage=1.0)
cat ../../../REQUIREMENTS.json                     # pinned 12-requirement checklist
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(|\.only\(" test src --include="*.ts" | wc -l   # 0 skips
grep -rnE "^\s*it\(" test --include="*.ts" | wc -l # 24 tests
# npm ci && npm test                               # would rebuild+run (skipped: cached scores authoritative)
```
