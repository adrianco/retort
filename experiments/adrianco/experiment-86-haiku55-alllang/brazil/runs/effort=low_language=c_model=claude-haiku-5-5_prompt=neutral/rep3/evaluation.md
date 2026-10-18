# Evaluation: effort=low_language=c_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=c, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 618 passed / 0 failed / 0 skipped (618 effective)
- **Build:** pass — from `scores.json` (`defect_rate=1.0`, `test_coverage=1.0`); `cc -std=c11 -Wall -Wextra -Wpedantic`
- **Lint:** pass — `code_quality=1.0` (warning-clean build with -Wall -Wextra -Wpedantic)
- **Architecture:** `run-summary` skill unavailable in this session — module map inlined below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

A clean, dependency-free C11 implementation: a stdio JSON-RPC 2.0 MCP server over five soccer tools, backed by a shared CSV loader, team-name normaliser, and a single-predicate query engine. Scores read from `scores.json` (inline gate), not re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/mcp.c:46` dispatches initialize/ping/tools/list/tools/call (JSON-RPC 2.0); `src/main.c:28` stdio loop; `src/tools.c:272` registers 5 tools |
| R2 | Loads datasets from data/kaggle | ✓ implemented | `src/dataset.c:23` SOURCES maps 5 match CSVs + `load_players` reads fifa_data.csv; log "Loaded 20102 matches and 18207 players" |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/query.c:35` match_passes + team_at; `venue` filter home/away/any in `src/tools.c:53` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/query.c:38-40` season + from/to on `m->ymd`; `build_filter` parses dates `src/tools.c:41-52` |
| R5 | Filter by competition | ✓ implemented | `src/query.c:37` contains_fold on competition; canonicalised in `src/dataset.c:39` across Brasileirao/Copa do Brasil/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/query.c:72` query_record; `tool_team_record` `src/tools.c:106`; test "Corinthians home 2022" played=19, W12 D4 L3 |
| R7 | Player search by name | ✓ implemented | `src/query.c:214` name via contains_fold; `tool_player_search` `src/tools.c:191`; Neymar lookup returns Overall 92 |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/query.c:215-217` nationality/club/position filters, overall returned; PSG club filter test passes (see P1 for data note) |
| R9 | Season standings from match results | ✓ implemented | `src/query.c:128` query_standings (3pts win/1 draw), `cmp_standing` tiebreaks; 2019 table = Flamengo 90pts/38p (correct) |
| R10 | Aggregate stats (avg goals, home vs away, biggest wins) | ✓ implemented | `src/query.c:187` query_stats: avg_goals, home/draw/away win rates, top-3 biggest wins; Brasileirao avg 2.56 |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query.c:145` query_head_to_head; surfaced in `tool_search_matches` `src/tools.c:93`; Fla-Flu 18-14-13 |
| R12 | Automated tests covering query capabilities | ✓ implemented | `tests/test_main.c` — 17 Given/When/Then scenarios, 618 checks, 0 failed; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per evaluate-run step 2):

```text
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.635, "idiomatic": 0.7, "token_efficiency": 0.009}
```

Final test run recorded in `_agent_stdout.log`:

```text
cc -std=c11 -Wall -Wextra -Wpedantic -O2 -D_POSIX_C_SOURCE=200809L -Isrc ...
./build/test_runner data/kaggle
Loaded 17128 matches and 18207 players from data/kaggle
... 17 scenarios ...
618 checks, 0 failed
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 2,033 (src); 453 (tests); 2,486 total |
| Files (excl. build/data) | 30 |
| Dependencies | 0 (C11 stdlib only) |
| Tests total | 618 checks / 17 scenarios |
| Tests effective | 618 |
| Skip ratio | 0% |
| Build duration | n/a (scored inline; not re-run) |

## Findings

No critical/high/medium/low findings. Top items (full list in `findings.jsonl`):

1. [info] fifa_data.csv carries almost no Brazilian-club players — club filters for Brazilian clubs return empty (data limitation, R8 met via nationality + other clubs)
2. [info] Top-scorers query not implemented (optional spec item only, not a required capability; no goalscorer column in data)
3. [info] Cross-source fixture dedupe may collapse same-day same-score fixtures (intentional overlap merge; tests pass)

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=c_model=claude-haiku-5-5_prompt=neutral/rep3
cat scores.json                       # stored mechanical scores (do not re-run)
grep -aE "checks, [0-9]+ failed" _agent_stdout.log | tail -1
# full rebuild (optional, not needed for scoring):
make test DATA=data/kaggle
```
