# Evaluation: language=typescript_model=sonnet_prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented (0 partial-by-omission, 0 missing) — but 3 carry correctness defects (see Findings; standings/stats double-count overlapping seasons)
- **Tests:** 46 passed / 0 failed / 0 skipped (46 effective) — from `test_coverage=0.9916` in `scores.json`
- **Build:** pass — `defect_rate=1.0` (build+test succeeded; not re-run)
- **Lint:** pass — `code_quality=0.733` (stored quality score; no separate warning count)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 0 low, 1 info)

The neutral prompt prescribes no methodology, so there are no `P*` prompt requirements — TASK.md (via the pinned `REQUIREMENTS.json`) is the whole spec.

## Requirements

Checklist is the pinned `experiment-14/REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/index.ts:22` Server + `ListTools`/`CallTool` handlers, 9 tools registered |
| R2 | Load & use provided CSVs in data/kaggle/ | ✓ implemented | `src/data-loader.ts:135-279` reads all 6 CSVs via csv-parse |
| R3 | Match query by team (home/away/either) | ✓ implemented* | `src/query-engine.ts:137-146` matchesTeamFilter — *over-broad substring match (medium) |
| R4 | Match query by date range / season | ✓ implemented* | `src/query-engine.ts:148-166` — *drops unparseable dates (low) |
| R5 | Match query by competition | ✓ implemented | `src/query-engine.ts:130-135,168-223` per-competition gating |
| R6 | Team W/L/D record + goals for/against | ✓ implemented* | `src/query-engine.ts:257-294` getTeamStats — *double-counts 2012-2019 (high) |
| R7 | Player search by name | ✓ implemented | `src/query-engine.ts:416-419` queryPlayers name filter |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `src/query-engine.ts:420-434` nationality/club/position/overall filters |
| R9 | Season standings computed from matches | ✓ implemented* | `src/query-engine.ts:347-401` getStandings — *double-counts 2012-2019 (high) |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented* | `src/query-engine.ts:451-516` getLeagueStats/getBiggestWins/getTopScoringTeams — *double-counts (high) |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query-engine.ts:307-332` getHeadToHead W/L/D + goals |
| R12 | Automated tests over query capabilities | ✓ implemented | `src/index.test.ts` 46 tests, 9 describe blocks; `test_coverage=0.9916` |

\* implemented but correctness-flawed — see Findings. The capability exists and is tested; the defect is in result accuracy, not presence.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2).

```text
scores.json: test_coverage=0.9916, defect_rate=1.0, code_quality=0.733,
             maintainability=0.609, idiomatic=0.57, token_efficiency=1.0
=> build+test succeeded; 46/46 tests pass; 0 skipped.
```

Skip scan (src/): no `.skip` / `xit` / `xdescribe` / `it.todo` found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .ts) | 1,118 (data-loader 280 + query-engine 516 + index 322) |
| Test LOC | 339 |
| Source files | 4 (3 modules + 1 test) |
| Tracked files (excl. node_modules, data/) | 19 |
| Dependencies | 7 (2 runtime, 5 dev) |
| Tests total | 46 |
| Tests effective | 46 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. **[high] R9 — Standings & team/aggregate stats double-count overlapping 2012–2019 seasons.** `getStandings` sums both `store.brasileirao` (2012–2022) and `store.historical` (2003–2019); `queryMatches` emits each overlapping match twice because the dedup key includes the competition label. Verified the season overlap is 2012–2019. Tests pass because assertions are inequalities. Affects R6, R9, R10.
2. **[medium] R3 — Bidirectional substring team matching conflates distinct clubs** (e.g. "Atletico" merges Atletico-MG/PR/GO). `query-engine.ts:12-16`.
3. **[medium] R4 — Date-range filter silently drops rows with unparseable dates** (extended dataset). `query-engine.ts:148-161`.
4. **[info] enhancement — Extra `get_top_scoring_teams` / `get_dataset_info` tools beyond spec.**

## Reproduce

```bash
cd experiment-14/runs/language=typescript_model=sonnet_prompt=neutral/rep1
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src/   # skip scan -> none
grep -cE "^\s*test\(" src/index.test.ts           # 46 tests
# verify the double-count: confirm season overlap between the two Brasileirão CSVs
python3 -c "import csv;b={r['season'] for r in csv.DictReader(open('data/kaggle/Brasileirao_Matches.csv'))};h={r['Ano'] for r in csv.DictReader(open('data/kaggle/novo_campeonato_brasileiro.csv'))};print(sorted(set(b)&set(h)))"
```
