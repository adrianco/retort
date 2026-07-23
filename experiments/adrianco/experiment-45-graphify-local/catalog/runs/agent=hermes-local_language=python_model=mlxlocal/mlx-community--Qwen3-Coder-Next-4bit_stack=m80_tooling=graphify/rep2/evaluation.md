# Evaluation: python · hermes-local · Qwen3-Coder-Next-4bit · m80 · graphify · rep 2

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, tooling=graphify, stack=m80
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — test_coverage=0.99 (from scores.json)
- **Lint:** pass — code_quality=0.833 (from scores.json)
- **No-regression:** pass — no_regression=1.0 (original 6 tests unchanged & green)
- **Architecture:** `run-summary` skill unavailable in this environment; module map summarized inline below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (11 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records reservation when 0 copies available | ✓ implemented | `catalog/loans.py:52-66`; test `test_reserve_when_unavailable` |
| R2 | reserve() raises when copies still available | ✓ implemented | `catalog/loans.py:58-59`; test `test_reserve_when_available_raises` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/loans.py:54-57`; tests `test_reserve_unknown_member_raises`, `test_reserve_unknown_book_raises` |
| R4 | member cannot hold two reservations for same book | ✓ implemented | `catalog/loans.py:61-63`; test `test_reserve_duplicate_raises` |
| R5 | list_reservations returns FIFO order | ✓ implemented | `catalog/store.py:32-33` preserves insertion order, `catalog/loans.py:77-80`; test `test_list_reservations_fifo` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:41-48` (removes earliest, re-loans to reserver, availability stays 0); test `test_reservation_fulfilled_on_return` |
| R7 | cancel_reservation removes a pending reservation | ✓ implemented | `catalog/loans.py:68-74`; test `test_cancel_reservation` |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `catalog/loans.py:75`; test `test_cancel_reservation_no_such_reservation` |
| R9 | new behavior exposed through Catalog facade | ✓ implemented | `catalog/service.py:27-34` (reserve / cancel_reservation / list_reservations) |
| R10 | new tests cover reservation behavior | ✓ implemented | 9 new tests in `tests/test_catalog.py:60-129` (≥3 required) |
| R11 | pre-existing suite passes unchanged | ✓ implemented | original 6 tests unmodified (`tests/test_catalog.py:17-57`); no_regression=1.0 |

## Build & Test

Scores read from `scores.json` (no re-run per evaluate-run skill):

```text
test_coverage   = 0.99   (build + tests pass; gate met)
code_quality    = 0.833
no_regression   = 1.0
defect_rate     = 1.0
token_efficiency= 0.0108
```

Agent stdout confirms: "All 15 tests pass." — 6 original + 9 new reservation tests, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 308 |
| Python files | 6 |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| New reservation tests | 9 |
| Graphify graph | 45 nodes / 101 edges / 10 files (`graphify-out/GRAPH_REPORT.md`) |

## Architecture (inline — run-summary unavailable)

Clean layering preserved exactly as the task required:
- **`models.py`** — added `Reservation(book_id, member_id)` dataclass alongside Book/Member/Loan.
- **`store.py`** — added `_reservations: list[Reservation]` with `add_reservation`/`get_reservations`/`remove_reservation`; FIFO order guaranteed by list append + filtered read.
- **`loans.py`** — new `ReservationError`; `reserve`/`cancel_reservation`/`list_reservations`; `return_book` extended to fulfill the earliest reservation on return (re-loans to the reserver so availability stays 0).
- **`service.py`** — `Catalog` facade re-exports `ReservationError` and delegates the three new methods.

## Findings

Full list in `findings.jsonl`:

1. [low] `Catalog.reserve`/`cancel_reservation` drop the `LoanService` return value — cosmetic API inconsistency, no requirement or test depends on it.

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=graphify/rep2
cat scores.json                              # stored mechanical scores
python -m pytest tests/test_catalog.py -q    # 15 passed
grep -rE "pytest\.skip|xfail" tests/         # 0 skips
```
