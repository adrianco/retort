# Evaluation: language=python_model=sonnet_prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, model=sonnet, prompt=ATDD (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — import + collection succeeded (test gate, `test_coverage=1.0`)
- **Lint:** pass — `code_quality=0.667` from `scores.json` (ruff cache present, no errors blocking)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low, 1 info)

Stored mechanical scores (from `scores.json`, not re-run): test_coverage=1.0,
code_quality=0.667, defect_rate=0.277, maintainability=0.735, idiomatic=0.68,
token_efficiency=0.0085.

## Requirements

Checklist is the pinned `experiment-13/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `server.py:8` `FastMCP`, 6 `@mcp.tool()` handlers, `mcp.run()` at `server.py:434` |
| R2 | Load/use datasets in data/kaggle/ | ✓ implemented | `data_loader.py:70-144` reads the supplied CSVs (matches + FIFA) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `data_loader.py:217-223` masks both `norm_home` and `norm_away` |
| R4 | Filter by date range and/or season | ✓ implemented | `data_loader.py:189-205` season + date_from/date_to |
| R5 | Filter by competition (Bra/Copa/Liberta) | ✓ implemented | `data_loader.py:12-22,185-187` alias map + filter; AC-3/12/13 |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `data_loader.py:302-338` `compute_team_stats`; `get_team_stats` tool |
| R7 | Player search by name | ✓ implemented | `data_loader.py:237-238`; AC-11 `test_find_players_by_name` |
| R8 | Players by nationality/club, with ratings | ✓ implemented | `data_loader.py:240-247` returns `Overall`; AC-5/6 |
| R9 | Season standings from match results | ✓ implemented | `data_loader.py:254-300` `compute_standings`; AC-7 (Flamengo 2019) |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `server.py:304-426` `get_top_stats`; AC-10/14 |
| R11 | Head-to-head between two teams | ✓ implemented | `data_loader.py:340-360` `compute_head_to_head`; AC-8 (see F1 caveat) |
| R12 | Automated tests covering queries | ✓ implemented | `tests/test_acceptance.py` 16 tests; `test_coverage=1.0` |

**Prompt-factor (ATDD) conformance:** acceptance tests drive the system only through the
public MCP interface (`mcp.call_tool`, `tests/test_acceptance.py:21-23`), assert on domain
behavior (WHAT not HOW), and read as external-user stories — strong adherence. One gap: the
prompt also asks for "finer-grained unit TDD underneath"; only the acceptance tier exists
(finding P4).

## Build & Test

Build/test were **not re-run** — stored scores were read from `scores.json` per skill policy.

```text
scores.json: {"test_coverage": 1.0, ...}
=> test gate PASS: server imports, 16 acceptance tests collected and all pass.
```

```text
grep skip/xfail in tests/: 0
test functions: 16  ->  effective = 16 (passed) + 0 (failed), 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 794 (server.py 434 + data_loader.py 360) |
| Lines of code (tests) | 267 |
| Files (.py, excl. caches) | 3 |
| Dependencies | 4 (mcp, pandas, pytest, pytest-asyncio) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (scores read, not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — `get_head_to_head` season filter is inconsistent: totals ignore season while only the displayed matches are filtered (`server.py:286-287` vs `data_loader.py:340`).
2. [medium] P4 — ATDD prompt asked for unit TDD underneath; only acceptance tests exist (`tests/` has one file, no unit tests of `data_loader` helpers).
3. [low] F2 — `BR-Football-Dataset.csv` is loaded but never merged into `all_matches`, so it is unqueryable; AC-12's "all six sources" claim re-queries the unified frames (`data_loader.py:160`).
4. [low] F3 — substring team matching can over-match short queries (`data_loader.py:217-223`).
5. [info] F4 — performance tests assert on wall-clock time, environment-sensitive (`tests/test_acceptance.py:251-267`).

No critical or high findings: all 12 pinned requirements are implemented and the full
acceptance suite passes.

## Reproduce

```bash
cd "experiment-13/runs/language=python_model=sonnet_prompt=ATDD/rep2"
cat scores.json                                   # stored mechanical scores (test gate)
cat ../../../REQUIREMENTS.json                     # pinned R1–R12 checklist
cat ../../../prompts/ATDD.md                        # prompt-factor instructions
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # skip count = 0
grep -rEc "def test_" tests/test_acceptance.py     # 16 test functions
# (Optional, not required) full re-run: python -m pytest tests/ -q
```
