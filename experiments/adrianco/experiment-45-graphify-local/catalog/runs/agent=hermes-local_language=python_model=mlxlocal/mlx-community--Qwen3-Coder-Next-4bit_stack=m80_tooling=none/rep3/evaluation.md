# Evaluation: hermes-local · python · Qwen3-Coder-Next-4bit · m80 · tooling=none · rep 3

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, stack=m80, tooling=none
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R11)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — 6 pre-existing + 9 new reservation tests
- **Build:** pass (Python, no build step) — from `test_coverage=0.99` in scores.json
- **Lint:** pass — `code_quality=0.83` in scores.json; 1 low finding (dead method)
- **No-regression:** pass — `no_regression=1.0` (original suite unchanged & green)
- **Architecture:** run-summary skill not available in this session; module map inlined below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

Pinned checklist from `catalog/REQUIREMENTS.json` (constant denominator = 11).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records reservation when 0 copies available | ✓ implemented | `catalog/loans.py:59-72` reserve(); test `test_reserve_unavailable_book` |
| R2 | reserve() raises when copies still available | ✓ implemented | `catalog/loans.py:65-66` `available()>0` → ReservationError; test `test_reserve_available_book_raises` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/loans.py:61-64`; tests `test_reserve_unknown_member_raises`, `test_reserve_unknown_book_raises` |
| R4 | member cannot hold two reservations for same book | ✓ implemented | `catalog/loans.py:68-70` duplicate check; test `test_reserve_duplicate_raises` |
| R5 | list_reservations() returns members FIFO | ✓ implemented | `catalog/store.py:35-36` order-preserving filter + `loans.py:82-84`; test `test_multiple_reservations_fulfill_earliest` asserts `[11, 10]` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:41-52` takes `reservations[0]`, cancels it, appends loan → availability stays 0; tests `test_fulfill_reservation_on_return`, `test_multiple_reservations_fulfill_earliest` |
| R7 | cancel_reservation() removes a pending reservation | ✓ implemented | `catalog/loans.py:74-78` + `store.py:38-42`; test `test_cancel_reservation` |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `catalog/loans.py:76-77`; test `test_cancel_reservation_none_raises` |
| R9 | new behavior exposed via Catalog facade | ✓ implemented | `catalog/service.py:26-37` reserve/cancel_reservation/list_reservations |
| R10 | new tests cover reservation behavior | ✓ implemented | 9 new tests in `tests/test_catalog.py:60-136` (≥3 required) |
| R11 | pre-existing suite still passes unchanged | ✓ implemented | original 6 tests intact `tests/test_catalog.py:15-57`; `no_regression=1.0` |

## Build & Test

Not re-run — stored scores used per skill (Step 2).

```text
scores.json
test_coverage = 0.99   # build + tests execute; ~1 line uncovered
no_regression = 1.0    # original tests/test_catalog.py suite green
defect_rate   = 1.0
code_quality  = 0.833
```

```text
_agent_stdout.log
All 15 tests pass. (6 pre-existing + 9 new reservation tests)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, catalog/) | 186 |
| Lines of code (tests) | 136 |
| Files (.py) | 6 |
| Dependencies | 0 (stdlib only) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted) |

## Architecture (run-summary unavailable)

Existing layering preserved exactly:
- `models.py` — added `Reservation(book_id, member_id)` dataclass alongside Book/Member/Loan.
- `store.py` — added `_reservations: list[Reservation]` with add/remove/get/cancel; FIFO preserved by append + order-preserving filter.
- `loans.py` — added `ReservationError`, `reserve()`, `cancel_reservation()`, `list_reservations()`; `return_book()` extended to fulfil the earliest reservation.
- `service.py` — `Catalog` facade re-exports the three new methods; `ReservationError` re-exported for tests.

## Findings

1. [low] `Store.remove_reservation` is defined but never called — dead code, likely the single line behind `test_coverage=0.99` (`catalog/store.py:33`).

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=none/rep3
cat scores.json                              # stored build/test/lint scores
python -m pytest tests/test_catalog.py -q    # 15 passed (matches .retort-regression.json cmd)
```
