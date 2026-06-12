# Evaluation: language=python_model=sonnet_prompt=TDD · rep 2

## Summary

- **Factors:** language=python, model=sonnet, prompt=TDD (tooling=none)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Prompt conformance:** P1 (TDD test-first) — followed (see below)
- **Tests:** 45 passed / 0 failed / 0 skipped (45 effective) — from `test_coverage=1.0`
- **Build:** pass — from `scores.json` `test_coverage=1.0` (build+tests ran; not re-run)
- **Lint:** pass with deductions — `code_quality=0.667` (not re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 2 info)

## Requirements

Pinned checklist from `experiment-13/REQUIREMENTS.json` (constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:19` FastMCP + 7 `@mcp.tool()`; `tests/test_server.py:28` asserts registration |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data_loader.py:61-141` reads all 6 CSVs; all present in `data/kaggle/` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `query_engine.py:45` + `_team_mask` `:19`; `test_query_engine.py:84` |
| R4 | Filter by date range and/or season | ✓ implemented | `query_engine.py:48-62`; `test_query_engine.py:92,104` |
| R5 | Filter by competition | ✓ implemented | `query_engine.py:51`; competitions tagged in loaders `:68,80,92`; `test_query_engine.py:98` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `query_engine.py:116 get_team_stats`; `test_query_engine.py:152-180` |
| R7 | Player search by name | ✓ implemented | `query_engine.py:186`; `test_query_engine.py:185` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `query_engine.py:189-199`; `test_query_engine.py:192,198` |
| R9 | Season standings computed from matches | ✓ implemented | `query_engine.py:206 get_standings` (points from results); `test_query_engine.py:217-237` |
| R10 | Aggregate stats | ✓ implemented | `query_engine.py:238 get_biggest_wins`, `:256 competition_averages`; `test_query_engine.py:242-266` |
| R11 | Head-to-head between two teams | ✓ implemented | `query_engine.py:69 head_to_head`; `test_query_engine.py:118-147` |
| R12 | Automated tests of query capabilities | ✓ implemented | 45 tests across 3 files; `test_coverage=1.0` |

### Prompt factor (TDD)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Test-first TDD: failing test → minimal code → refactor, ending in thorough unit coverage | ✓ followed (structurally) | Tests and implementation share matching "Cycle 1–9" sectioning (`test_data_loader.py:9`/`data_loader.py:7`, `test_query_engine.py:82`/`query_engine.py:32`); 45 unit tests covering every public method; query-engine tests use in-memory fixtures, not CSV I/O. Red→green ordering itself isn't observable post-hoc, but the incremental cycle structure and coverage are consistent with TDD. |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill step 2):

```text
scores.json: test_coverage=1.0, code_quality=0.6667, defect_rate=0.9011,
             maintainability=0.9202, idiomatic=0.62, token_efficiency=0.0347
```

`test_coverage=1.0` ⇒ build + all 45 tests passed. Skip scan over `tests/*.py` found 0 skips/xfails.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 626 (data_loader 164 + query_engine 283 + server 179) |
| Lines of code (tests) | 422 |
| Files (excl. artifacts/data) | 16 (3 src, 3 test + `__init__`, configs) |
| Dependencies | 2 (`mcp>=1.0.0`, `pandas>=2.0.0`) |
| Tests total | 45 |
| Tests effective | 45 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — Aggregation does not guard against NaN goal values (`query_engine.py:154`)
2. [low] F2 — Code quality below clean (`code_quality=0.667`)
3. [low] F3 — `get_standings` recomputes `get_team_stats` per team, O(teams × matches)
4. [info] F4 — Competition filter expects internal keys, not human-readable names
5. [info] F5 — Aggregation uses `iterrows()` instead of vectorized pandas

No critical or high findings — the run satisfies the full spec with passing tests and no skips.

## Reproduce

```bash
cd experiment-13/runs/language=python_model=sonnet_prompt=TDD/rep2
cat scores.json                              # mechanical scores (build/test/lint)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # skip scan (none)
grep -rE "^def test_" tests/*.py | wc -l     # 45 tests
# Optional re-run (skill says rely on scores.json instead):
# PYTHONPATH=. python -m pytest tests/ -q
```
