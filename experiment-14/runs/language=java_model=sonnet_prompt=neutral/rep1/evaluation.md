# Evaluation: language=java_model=sonnet_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=sonnet, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 61 passed / 0 failed / 0 skipped (61 effective) — per `test_coverage=1.0`
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` (retort.db; not re-run)
- **Lint:** pass — `code_quality=1.0` (retort.db)
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Prompt factor `neutral` prescribes no methodology (`prompts/neutral.md`), so there are no
additional `P*` requirements; the pinned `REQUIREMENTS.json` (R1–R12) is the full checklist.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `McpServer.java:61` dispatches initialize/tools/list/tools/call; 9 tools registered at `:85-165` |
| R2 | Loads provided datasets in data/kaggle/ | ✓ implemented | `DataLoader.java:27-32` loads all 6 CSVs via OpenCSV |
| R3 | Match query by team (home/away/either) | ✓ implemented | `MatchTools.java:34-35` filters home or away via `TeamNormalizer.matches` |
| R4 | Match query by date range and/or season | ✓ implemented | `MatchTools.java:37-39` season + start/end date; `normDate` (`:381`) normalizes DD/MM/YYYY→ISO |
| R5 | Match query by competition | ✓ implemented | `MatchTools.java:36` competition filter; competitions set per source (`DataLoader.java:59,88,117`) |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `MatchTools.teamStats` (`:144`) aggregates wins/draws/losses, goalsFor/Against, points |
| R7 | Player search by name | ✓ implemented | `PlayerTools.searchPlayers` (`:35`) / `playerProfile` (`:84`) filter by name |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `PlayerTools.java:36-38` nationality/club filters; output includes Overall (`:68`) |
| R9 | Season standings from match results | ✓ implemented | `MatchTools.standings` (`:236`) computes points (3/1/0) from matches |
| R10 | Aggregate statistics | ✓ implemented | `MatchTools.matchStatistics` (`:302`) supports biggest_wins / goals_avg / home_away |
| R11 | Head-to-head between two teams | ✓ implemented | `MatchTools.headToHead` (`:66`) returns W/L/D between two teams |
| R12 | Automated tests covering queries | ✓ implemented | 61 `@Test` across 5 test files; `test_coverage=1.0` (all pass, 0 skips) |

## Build & Test

Build/test/lint were **not re-run** — stored scores from `experiment-14/retort.db`
(cross-checked against `scores.json`) stand in:

```text
test_coverage = 1.0   # build succeeded + all tests executed and passed
defect_rate   = 1.0   # build+test success
code_quality  = 1.0   # lint/quality
maintainability = 0.686
idiomatic     = 0.62
```

Test inventory (grepped, not executed): 61 `@Test` methods, 0 `@Disabled`/`@Ignore`/`assume*`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main) | 1,438 |
| Lines of code (test) | 641 |
| Files (excl. data/, target/) | 17 |
| Dependencies (pom) | 4 (jackson-databind, jackson-annotations, opencsv, junit-jupiter) |
| Tests total | 61 |
| Tests effective | 61 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; run took 468s end-to-end) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium findings.

1. [low] search_matches sorts on raw `datetime`, mixing ISO and DD/MM/YYYY-origin rows (`MatchTools.java:40` vs `normDate:381`) — filtering is correct, only cross-dataset ordering can be off.
2. [low] Data classes (`Player`, `Match`) use public mutable fields rather than records/encapsulation — consistent with `idiomatic=0.62`.
3. [info] Nine MCP tools registered, exceeding the minimum required capabilities.
4. [info] Date-range filtering correctly normalizes mixed CSV date formats (positive evidence for R4).

## Reproduce

```bash
cd experiment-14/runs/language=java_model=sonnet_prompt=neutral/rep1
# Scores read from the experiment DB (do not re-run the toolchain):
sqlite3 -readonly ../../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id = (SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='java'
      AND json_extract(er.run_config_json,'\$.model')='sonnet'
      AND json_extract(er.run_config_json,'\$.prompt')='neutral'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
# Test inventory:
grep -rE "@Test" src/test --include="*.java" | wc -l
grep -rnE "@Disabled|@Ignore|assume(True|False)" src/test --include="*.java" | wc -l
```
