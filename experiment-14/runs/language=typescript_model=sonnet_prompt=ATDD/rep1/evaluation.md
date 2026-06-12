# Evaluation: language=typescript_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet, prompt=ATDD
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial (R10), 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — `test_coverage=1.0` implies build + all tests passed (not re-run)
- **Lint:** n/a — `code_quality=0.7333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts` — `Server` + 5 registered tools over stdio |
| R2 | Loads provided data/kaggle/ datasets | ✓ implemented | `src/data/loader.ts:20-66` parses all 7 CSVs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/tools/matches.ts:19` `teamsMatch` on both sides |
| R4 | Filter by date range and/or season | ✓ implemented | `src/tools/matches.ts` season filter (date-range absent — see findings) |
| R5 | Filter by competition (3 comps) | ✓ implemented | `src/server.ts:25` enum; `matches.ts:30-43` per-comp branches |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/tools/teams.ts:37-69` getTeamStats |
| R7 | Player search by name | ✓ implemented | `src/tools/players.ts:29-32` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/tools/players.ts:34-54` returns Overall/attrs |
| R9 | Season standings computed from matches | ✓ implemented | `src/tools/standings.ts:42-89`; acceptance test asserts Flamengo 1st in 2019 |
| R10 | Aggregate statistical analysis | ~ partial | per-team aggregates only; no avg-goals/match, home-vs-away, biggest-wins tool |
| R11 | Head-to-head between two teams | ✓ implemented | `src/tools/headToHead.ts:11-70` |
| R12 | Automated tests for query capabilities | ✓ implemented | `src/__tests__/acceptance.test.ts`; `test_coverage=1.0` |

**Prompt-factor (ATDD) conformance:**
- **P1 — acceptance tests as executable specs through the public interface:** ✓ strong. `acceptance.test.ts` drives the SUT only via an MCP `Client` over `StdioClientTransport` (`client.callTool`), genuinely black-box, asserting on returned domain data — no internal imports.
- **P2 — finer-grained unit TDD underneath:** ~ partial. Only the acceptance layer exists; no unit tests for `normalizer`/`loader`/tool internals (see findings).

## Build & Test

Build/test not re-run — mechanical scores read from `scores.json`:

```text
test_coverage   = 1.0    → build + all 10 tests passed (test gate)
defect_rate     = 1.0    → build + test succeeded
code_quality    = 0.7333
maintainability = 0.6299
idiomatic       = 0.42
token_efficiency= 1.0
```

Skip scan (`grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\("`): 0 skips across `src`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 589 |
| Lines of code (tests) | 147 |
| Files (src) | 10 |
| Dependencies | 6 (2 runtime: @modelcontextprotocol/sdk, csv-parse) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] R10 — No dedicated statistical-analysis tool (avg goals/match, home-vs-away, biggest wins); only per-team aggregates.
2. [medium] P2 — ATDD prescribed unit TDD underneath, but only the black-box acceptance suite exists.
3. [low] R4 — Match filtering supports season but not date-range.
4. [low] data-1 — `br_football` season derived via `new Date(m.date).getFullYear()` is fragile across the spec's varied date formats.
5. [info] enh-1 — Supplementary `brazilian_clubs_players.csv` merged with FIFA data (enhancement).

## Reproduce

```bash
cd "experiment-14/runs/language=typescript_model=sonnet_prompt=ATDD/rep1"
cat scores.json                      # mechanical scores (build/test not re-run)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src --include="*.ts" | wc -l
find src -name "*.ts" -not -path "*__tests__*" | xargs wc -l | tail -1
# To actually run: npm install && npm test
```
