# Evaluation: language=java_model=sonnet_tooling=beads · rep 1

## Summary

- **Factors:** language=java, model=sonnet, tooling=beads
- **Status:** cannot-verify (production source code missing from archive)
- **Requirements:** 0/12 implemented, 12 partial, 0 missing (all cannot-verify due to absent src/main)
- **Tests:** 44 passed / 0 failed / 0 skipped (44 effective) — per test_coverage=1.0 from retort.db
- **Build:** pass — test_coverage=1.0, defect_rate=1.0 from retort.db (cannot reproduce: src/main absent)
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 13 items in `findings.jsonl` (1 critical, 11 high, 1 medium)

## Critical Note

**The `src/main` directory is entirely missing from this archive.** Only test files exist under `src/test/`. The 5 test files (691 LOC) import production classes (`DataLoader`, `DataRepository`, `MatchTools`, `PlayerTools`, `TeamTools`, `TeamNameNormalizer`, `Match`, `Player`) that are not present. The previous evaluation (dated 2026-04-18) cited 9 source files / 1560 LOC and referenced specific line numbers in production code — those files no longer exist.

retort.db scores (test_coverage=1.0, code_quality=1.0, defect_rate=1.0) confirm the code existed and all 44 tests passed at scoring time. The archive appears to have lost the production source after scoring.

All 12 requirements are classified as `partial` (cannot-verify) — the tests strongly suggest each was implemented and working, but the production source cannot be inspected.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server with tools/handlers | ~ partial | pom.xml:108 mainClass=BrazilianSoccerMcpServer; MCP SDK dep at pom.xml:28; server class absent |
| R2 | Loads datasets from data/kaggle/ | ~ partial | DataLoaderTest tests 6 CSV loaders; test_coverage=1.0; DataLoader.java absent |
| R3 | Match query: find by team | ~ partial | MatchToolsTest.java:56 tests searchMatches("Palmeiras",...); source absent |
| R4 | Match query: filter by date range/season | ~ partial | MatchToolsTest.java:102 tests date range "2019-01-01"–"2019-12-31"; line 56 season=2022; source absent |
| R5 | Match query: filter by competition | ~ partial | MatchToolsTest.java:68 "Brasileirao", line 80 "Libertadores"; source absent |
| R6 | Team query: W/L/D record and goals | ~ partial | TeamToolsTest.java:43-46 asserts Record, Goals, Win rate, Home, Away; source absent |
| R7 | Player query: search by name | ~ partial | PlayerToolsTest.java:65 "Gabriel", line 130 "Neymar", line 152 "Ronaldo"; source absent |
| R8 | Player query: filter by nationality/club with ratings | ~ partial | PlayerToolsTest.java:37 nationality="Brazil", line 52 club="Flamengo", line 90 minOverall=85; source absent |
| R9 | Competition standings from match results | ~ partial | TeamToolsTest.java:63 getStandings(2019, "Brasileirao"); source absent |
| R10 | Statistical analysis: aggregate stats | ~ partial | TeamToolsTest.java:93 getGlobalStats asserts avg goals/match, home wins; MatchToolsTest.java:91 getBiggestWins; source absent |
| R11 | Head-to-head records between two teams | ~ partial | MatchToolsTest.java:38 headToHead("Flamengo","Fluminense",...); source absent |
| R12 | Automated tests covering query capabilities | ~ partial | 5 test files, 44 @Test methods, 0 skipped; test_coverage=1.0; but tests cannot compile without missing src/main |

## Build & Test

```text
Scores from retort.db (build/test NOT re-run — source code missing from archive):
  test_coverage  = 1.0  (build + all tests passed at scoring time)
  code_quality   = 1.0
  defect_rate    = 1.0  (build+test succeeded)
  idiomatic      = 0.7
  maintainability = 0.8049
  token_efficiency = 0.5
```

```text
Test results (from retort.db, confirmed by prior evaluation):
  Tests run: 44, Failures: 0, Errors: 0, Skipped: 0
  - DataLoaderTest: 7 tests
  - MatchToolsTest: 10 tests
  - PlayerToolsTest: 10 tests
  - TeamNameNormalizerTest: 7 tests
  - TeamToolsTest: 10 tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 691 (tests only; production code missing) |
| Source files | 5 (tests only) |
| Total files (excluding build artifacts) | 19 |
| Dependencies | 6 (MCP SDK, Jackson, Commons CSV, SLF4J, Logback, JUnit 5) |
| Tests total | 44 |
| Tests effective | 44 |
| Skip ratio | 0% |
| Build duration | N/A (not re-run; test_coverage=1.0 from retort.db) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Production source code missing from archive — src/main does not exist
2. [high] R1: MCP server entrypoint not verifiable — source missing
3. [high] R2: Data loading from data/kaggle/ not verifiable — DataLoader missing
4. [high] R3: Match query by team not verifiable — MatchTools missing
5. [high] R4: Date range/season filter not verifiable — source missing

## Reproduce

```bash
cd experiment-2/runs/language=java_model=sonnet_tooling=beads/rep1

# Verify archive state
ls src/main  # expected: directory not found
ls src/test/java/com/braziliansoccer/mcp/  # 5 test files

# Scores from retort.db
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='sonnet' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"

# Cannot reproduce build/test — src/main is missing
# mvn clean test  # would fail: cannot resolve imports
```
