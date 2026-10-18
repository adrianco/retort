# Evaluation: effort=low_language=java_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 56 passed / 0 failed / 0 skipped (56 effective)
- **Build:** pass — `test_coverage=1.0` from scores.json (build + all tests passed; not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Stored scores (`scores.json`): test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.834, idiomatic=0.30, token_efficiency=0.0077. The two low metrics (idiomatic, token_efficiency) are model/stack characterizations, not conformance defects — the spec is fully met.

## Requirements

Pinned checklist from `brazil/REQUIREMENTS.json` (R1–R12), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `mcp/McpServer.java:40` JSON-RPC 2.0 dispatch; `mcp/SoccerTools.java:172` registers 7 tools via `definitions()` |
| R2 | Loads/uses data/kaggle datasets | ✓ implemented | `data/DataLoader.java:541` reads all 6 CSVs; tests load `data/kaggle` (`SoccerDataBddTest.java:25`) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `search_matches` → `MatchFilter.Venue` + `Dataset.atVenue` (`Dataset.java:847`) |
| R4 | Filter by date range and/or season | ✓ implemented | `from`/`to`/`season` in `Dataset.passes` (`Dataset.java:834-842`) |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | competition filter (`Dataset.java:831`); constants `DataLoader.java:531-535` |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `team_record` → `Dataset.teamRecord` + `Tally` (`SoccerTools.java:273`, `Dataset.java:868`) |
| R7 | Player search by name | ✓ implemented | `find_players` name filter → `PlayerFilter.test` (`PlayerFilter.java:6`) |
| R8 | Players by nationality/club with ratings | ✓ implemented | `find_players` nationality/club/position/min_overall; output includes Overall/Potential (`SoccerTools.java:338`) |
| R9 | Standings computed from match results | ✓ implemented | `standings` → `Dataset.standings` 3/1/0 pts, sorted pts→GD→GF (`Dataset.java:747`) |
| R10 | Aggregate statistics | ✓ implemented | `aggregate_stats`: goals_per_match, outcome_rates, biggest_wins, best_home/away_record (`SoccerTools.java:362`) |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` → `Dataset.headToHead` (`Dataset.java:733`) |
| R12 | Automated tests covering queries | ✓ implemented | 56 `@Test` across 6 files; `test_coverage=1.0` |

No requirement is partial or missing.

## Build & Test

Not re-run — stored mechanical scores were used (per evaluate-run skill, step 2).

```text
scores.json
test_coverage = 1.0   # build + all tests passed
code_quality  = 1.0   # lint/quality gate
defect_rate   = 1.0   # build+test succeeded
```

```text
grep -rh "@Test" src/test --include="*.java" | wc -l  -> 56
grep -rnE "@Disabled|@Ignore|assumeTrue|assumeFalse" src/test  -> (none)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 1290 |
| Lines of code (test) | 767 |
| Files (src) | 18 |
| Dependencies (pom.xml) | 2 (Jackson databind, JUnit 5) |
| Tests total | 56 |
| Tests effective | 56 |
| Skip ratio | 0% |
| Build duration | not re-run (test_coverage=1.0) |

## Findings

All 4 findings are info-level enhancements (no defects):

1. [info] Hand-rolled JSON-RPC 2.0 MCP server, no MCP SDK dependency (Jackson only)
2. [info] Robust team-name normalization (state suffixes, aliases, accent folding) addressing the spec's name-variation note
3. [info] Cup finals inferred from last round per season
4. [info] 56 tests, zero skipped/disabled, BDD scenarios run against real datasets

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=java_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json
grep -rh "@Test" src/test --include="*.java" | wc -l
grep -rnE "@Disabled|@Ignore|assumeTrue|assumeFalse" src/test --include="*.java"
grep -o '[A-Za-z_]*\.csv' src/main/java/br/soccer/data/DataLoader.java | sort -u
```
