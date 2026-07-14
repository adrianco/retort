# Evaluation: language=python_model=opus-4.8-fast_prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, model=opus-4.8-fast, prompt=ATDD (tooling=none)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`) · prompt instruction P1 (ATDD) followed
- **Tests:** 50 collected / 0 skipped (50 effective) — tests executed under coverage (`test_coverage=0.46`); 7 acceptance + 2 unit files
- **Build:** pass — install/import succeeded (test_coverage=0.46 > 0 from scores.json; not re-run)
- **Lint:** pass with warnings — `code_quality=0.667` from scores.json; 6 ruff warnings (import order + line length)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 3 medium, 1 low, 1 info)

Mechanical scores read from `scores.json` (per skill: not re-run): `test_coverage=0.46`, `code_quality=0.667`, `defect_rate=0.923`, `maintainability=0.796`, `idiomatic=0.72`, `token_efficiency=0.0104`.

## Requirements

Checklist is the pinned `experiment-13/REQUIREMENTS.json` (R1–R12, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:24 create_server` FastMCP + 10 `@mcp.tool()`; `tests/acceptance/test_server_protocol.py:25` |
| R2 | Loads/uses provided data/kaggle CSVs | ✓ implemented | `data_loader.py:231 load_dataset`; all 6 CSVs present in `data/kaggle/` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `server.py:31 find_matches` venue param; `repository.py:61-69`; `test_match_queries.py:11,57` |
| R4 | Match filter by date range / season | ✓ implemented | `repository.py:55-59`; `test_match_queries.py:29,70` |
| R5 | Match filter by competition | ✓ implemented | `repository.py:53`; loaders for Brasileirão/Cup/Libertadores; `test_match_queries.py:44` |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `repository.py:119 team_record`; `test_team_queries.py:11,33,66` |
| R7 | Player search by name | ✓ implemented | `repository.py:315`; `server.py:118 search_players`; `test_player_queries.py:11` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `repository.py:317-322`; `server.py:138 top_players`; `test_player_queries.py:26,39,79` |
| R9 | Season standings computed from matches | ✓ implemented | `repository.py:165 standings`; `test_competition_queries.py:20,35,49` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `repository.py:243 statistics`, `:277 biggest_wins`; `test_statistics.py:11,27,42` |
| R11 | Head-to-head records | ✓ implemented | `repository.py:85 head_to_head`; `test_team_queries.py:47` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 50 tests, 0 skips, `test_coverage=0.46 > 0`; `tests/acceptance/*`, `tests/unit/*` |

### Prompt-factor instruction (prompt=ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Executable ATDD: acceptance tests through the public interface, domain language, atomic/isolated, drive implementation | ✓ followed | `tests/conftest.py:151 running()` drives a real MCP `ClientSession` over in-memory transport (no back-door); domain-language test names (`test_find_all_matches_between_two_teams`); each test seeds its own `tmp_path` dataset (`conftest.py:182`); unit TDD underneath (`tests/unit/`) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` per the skill (re-running the toolchain is pure duplication). Signals:

```text
test_coverage = 0.46   # tests executed under coverage; 46% line coverage
defect_rate   = 0.923  # low defect density (few lint/type/test defects per kloc)
code_quality  = 0.667  # ruff-based lint score
```

Skip scan (read-only):

```text
grep -rE "pytest.skip|@pytest.mark.skip|xfail" tests/  -> 0 matches
50 test functions across 9 files, 0 skipped -> 50 effective
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. blanks/comments) | ~1017 (`brazilian_soccer_mcp/`) |
| Lines of code (tests) | ~897 |
| Files (source modules) | 5 (+ `__init__.py`) |
| Test files | 9 (7 acceptance, 2 unit) |
| Dependencies | 1 runtime (`mcp>=1.0.0`) + 2 dev (pytest, pytest-asyncio) |
| Tests total | 50 |
| Tests effective | 50 |
| Skip ratio | 0% |
| Line coverage | 46% (test_coverage=0.46) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — `find_matches` default `limit=50` silently truncates and reports the truncated `count` (`server.py:39,56`).
2. [medium] F2 — `statistics()`/`biggest_wins()` double-count overlapping source CSVs (no `_dominant_source_only` dedup, unlike `standings()`) (`repository.py:243,277` vs `:167`).
3. [medium] F3 — Moderate line coverage (46%) despite 50 passing tests; loader/normalize edge branches unexercised.
4. [low] F4 — 6 ruff lint warnings (import ordering + line length), all auto-fixable.
5. [info] F5 — Robust normalization/dedup beyond the minimum spec (strength).

No critical, high, build, or test-execution failures. This is a clean, spec-complete ATDD run.

## Reproduce

```bash
cd experiment-13/runs/language=python_model=opus-4.8-fast_prompt=ATDD/rep2
# Mechanical scores (not re-run during eval):
cat scores.json
# Skip scan:
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
# Lint evidence:
ruff check brazilian_soccer_mcp tests
# (Optional) full test run:
pip install -e '.[dev]' && pytest
```
