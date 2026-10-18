# Evaluation: effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 41 scenarios passed / 0 failed / 0 skipped (41 effective) — `test_coverage=1.0`
- **Build:** pass (from `scores.json` test_coverage=1.0; build precedes the test gate)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/mcp_server.cpp:198` handleRequest (initialize/ping/tools/list/tools/call); 6 tools in `listTools()` |
| R2 | Loads provided datasets in data/kaggle/ | ✓ implemented | `src/dataset.cpp:79` load() reads all 6 CSVs; `data/kaggle/` has all 6 files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `findMatches` + `MatchFilter.team`/`venue`; `tests/query_tests.cpp:38` Fla-Flu |
| R4 | Filter by date range and/or season | ✓ implemented | `MatchFilter.season`/`dateFrom`/`dateTo`; `query_tests.cpp:53` Palmeiras 2023 |
| R5 | Filter by competition | ✓ implemented | `MatchFilter.competition`; Brasileirão/Copa do Brasil/Libertadores loaded; `test_main.cpp` competitions set |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `teamRecord()` → TeamRecord; `query_tests.cpp:78` consistency check |
| R7 | Player search by name | ✓ implemented | `searchPlayers` + `PlayerFilter.name`; `query_tests.cpp:151` case-insensitive name |
| R8 | Players by nationality/club with ratings | ✓ implemented | `PlayerFilter.nationality`/`club`; `query_tests.cpp:122` Brazilian players ≥80 |
| R9 | Season standings computed from matches | ✓ implemented | `standings()` 3/1/0 pts; `query_tests.cpp:89` Flamengo 2019 = 90 pts, 28W |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `goalStats()` → GoalStats; `query_tests.cpp:159` 2019 = 380 matches, rates sum 100% |
| R11 | Head-to-head between two teams | ✓ implemented | `headToHead()`; `query_tests.cpp:103` wins add up to played |
| R12 | Automated tests covering query capabilities | ✓ implemented | 41 TEST_CASEs across 4 files; `test_coverage=1.0` (built + all passed) |

## Build & Test

Build and tests were **not re-run** — scores were read from `scores.json` (inline-gate archive):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0109, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.6769, "idiomatic": 0.9}
```

`test_coverage=1.0` ⇒ the project compiled and all tests passed. The runner (`tests/test_main.cpp`)
reports `N scenario(s), M failed` and exits non-zero on any failure; a passing gate means M=0.
No `DISABLED_`/`SKIP`/skip markers found in `tests/`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,864 |
| Lines of code (incl. tests) | 2,421 |
| Files (src + tests) | 19 |
| Dependencies | 0 (std library only) |
| Tests total | 41 scenarios (~130 CHECK assertions) |
| Tests effective | 41 |
| Skip ratio | 0% |
| Build duration | not measured (scores from inline gate) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Extended-stats columns (shots/corners/attacks) loaded but not surfaced by any tool — `src/dataset.cpp:154`
2. [info] Zero external dependencies — JSON, CSV and test harness all hand-written
3. [info] Fixtures deduplicated across overlapping competition sources — `src/dataset.cpp:69`
4. [info] Team-name/accent/multi-format date normalization — `src/text.hpp`

No critical, high, or medium findings. This is a complete, spec-conforming run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (no re-run)
cat ../../REQUIREMENTS.json                        # pinned 12-requirement checklist
grep -rhE "^TEST_CASE\(" tests/ | wc -l            # 41 test scenarios
grep -rnE "DISABLED_|SKIP|\.skip" tests/           # 0 skips
# Optional full rebuild: cmake -S . -B build && cmake --build build && ./build/<test_target>
```
