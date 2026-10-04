# Evaluation: effort=low_language=typescript_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 88 passed / 0 failed / 0 skipped (88 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (build + all tests ran)
- **Lint:** pass — code_quality=0.7333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate, not re-run): `test_coverage=1.0`,
`defect_rate=1.0`, `code_quality=0.7333`, `maintainability=0.5271`, `idiomatic=0.58`,
`token_efficiency=0.0175`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts:10` `createServer()` registers 15 tools via `McpServer`/`StdioServerTransport` |
| R2 | Loads & uses `data/kaggle/` datasets | ✓ implemented | `src/data.ts:17` FILES maps the CSVs; `loadDataset()` reads them; `defaultDataDir()` resolves `data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:158` `findMatches` filters `m.home===team \|\| m.away===team`; tool `search_matches` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:172` `dateFrom/dateTo` + `season` filters; `search_matches` schema `season`,`date_from`,`date_to` |
| R5 | Filter by competition | ✓ implemented | `src/queries.ts:113` `resolveCompetition` maps Brasileirão/Copa do Brasil/Libertadores; used in `findMatches` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:203` `teamRecord` + `tabulate` (l.343); tool `team_stats` |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:284` `findPlayers` name folding; tools `search_players`, `player_profile` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `src/queries.ts:301` nationality/club filters; `playerLine` (tools.ts:63) shows Overall/Potential |
| R9 | Season standings computed from results | ✓ implemented | `src/queries.ts:239` `standings` sorts `tabulate` output by points (3/win); tool `standings` |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:256` `leagueStats` (avg goals, home/away/draw rates); `biggestWins`; tools `league_stats`,`biggest_wins` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:180` `headToHead` W/L/D + goals; tool `head_to_head` |
| R12 | Automated tests covering the queries | ✓ implemented | 4 test files, 88 passing cases; `tests/queries.test.ts` exercises the SoccerKB query surface; test_coverage=1.0 |

No prompt-factor requirements (`prompt=neutral` is a phrasing variant, no extra checkable instructions).

## Build & Test

```text
# Not re-run — read from scores.json (inline eval gate)
test_coverage = 1.0   ⇒ tsc build succeeded AND all tests executed and passed
defect_rate   = 1.0   ⇒ build + test success
```

```text
# vitest run (final run captured in _agent_stdout.log)
Test Files  4 passed (4)
Tests       88 passed (88)
```

Skip scan: `grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' tests/` → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests) | 1901 |
| Files (excl. node_modules/dist) | 30 |
| Dependencies (prod + dev) | 5 |
| Tests total | 88 |
| Tests effective | 88 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (all info — no defects; full list in `findings.jsonl`):

1. [info] Tool surface far exceeds spec (15 tools, incl. knockout brackets, derbies, season compare)
2. [info] Standings infer champion/relegation only when the season looks complete
3. [info] Sixth CSV (`novo_campeonato_brasileiro.csv`) loaded beyond the four spec'd match files
4. [info] 88 tests pass, 0 skipped, 0 disabled

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/brazil/runs/effort=low_language=typescript_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                                  # stored mechanical scores (no re-run)
grep -rnE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' tests/   # skip scan → 0
# Optional full re-run: npm ci && npm run build && npm test
```
