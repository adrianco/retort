# Evaluation: mlxlocal/Qwen3-Coder-Next-4bit · python · graphify · m80 · rep 1

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, tooling=graphify, stack=m80
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass — test_coverage=0.99, defect_rate=1.0 (from scores.json)
- **Lint:** pass — code_quality=0.83 (from scores.json)
- **No-regression:** pass — no_regression=1.0 (original 6-test suite intact)
- **Architecture:** run-summary skill unavailable in this environment; graphify tooling produced `graphify-out/GRAPH_REPORT.md` (45 nodes / 101 edges / 10 files)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records when 0 copies available | ✓ implemented | `catalog/loans.py:52-64` reserve(); `catalog/service.py:27` facade |
| R2 | reserve() raises when copies available | ✓ implemented | `catalog/loans.py:58-59`; test `tests/test_catalog.py:73` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/loans.py:54-57`; tests `test_catalog.py:81,89` |
| R4 | member cannot hold two reservations for a book | ✓ implemented | `catalog/loans.py:60-61` via `store.has_reservation`; test `:97` |
| R5 | list_reservations() FIFO order | ✓ implemented | `catalog/store.py:34-35` order-preserving filter; test `:106` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:41-48`; tests `:115,155,169` |
| R7 | cancel_reservation removes a pending reservation | ✓ implemented | `catalog/loans.py:66-78`; test `:137` |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `catalog/loans.py:69-70,77-78`; test `:147` |
| R9 | new behavior exposed through Catalog facade | ✓ implemented | `catalog/service.py:27-34` reserve/cancel_reservation/list_reservations |
| R10 | new tests cover reservation behavior | ✓ implemented | 12 new tests `tests/test_catalog.py:64-179` (spec asked >=3) |
| R11 | pre-existing suite still passes unchanged | ✓ implemented | no_regression=1.0; original tests `test_catalog.py:17-57` untouched |

## Build & Test

Not re-run — stored scores read from `scores.json` (per evaluate-run policy):

```text
python -m pytest tests/test_catalog.py -q --tb=short   (regression command, .retort-regression.json)
test_coverage = 0.99   → tests executed and passed (99% line coverage)
defect_rate   = 1.0    → build + test succeeded
no_regression = 1.0    → original 6-test suite passes against modified tree
code_quality  = 0.83
```

Agent's own report (`_agent_stdout.log`): "All 18 tests pass."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 184 (catalog/*.py) |
| Test LOC | 178 (tests/test_catalog.py) |
| Files (catalog + tests) | 6 |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| API calls (hermes) | 21 |
| Tokens (in/out) | 46,617 / 6,380 |

## Findings

Top items (full list in `findings.jsonl`) — all info-level; no defects:

1. [info] R10 — 12 new tests added (spec asked for >=3), covering FIFO, multi-copy, and auto-fulfill.
2. [info] Reservation state kept in Store, preserving the models/store/loans/service layering.
3. [info] reserve() permits a current loan-holder to also reserve the same book (unspecified edge; not prohibited by spec).

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=graphify/rep1
cat scores.json                                    # stored mechanical scores
python -m pytest tests/test_catalog.py -q --tb=short   # 18 passed
grep -rE "pytest\.skip|xfail" tests/ | wc -l       # 0 skips
```
