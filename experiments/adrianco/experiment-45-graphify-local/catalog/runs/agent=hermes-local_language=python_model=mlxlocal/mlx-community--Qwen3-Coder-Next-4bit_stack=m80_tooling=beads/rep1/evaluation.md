# Evaluation: hermes-local · python · Qwen3-Coder-Next-4bit · m80 · beads · rep 1

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, stack=m80, tooling=beads
- **Status:** ok — clean pass
- **Requirements:** 11/11 implemented, 0 partial, 0 missing
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective; 14 new reservation tests + 6 seed tests)
- **Build:** pass (test_coverage=1.0 from scores.json — tests executed and all passed)
- **Lint:** pass — code_quality=0.833 from scores.json (minor style residue, non-blocking)
- **No-regression:** pass — no_regression=1.0 (original 6-test seed suite unchanged behavior)
- **Architecture:** run-summary skill unavailable in this session — not generated
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records when 0 copies available | ✓ implemented | `catalog/loans.py:48-61`; test `test_reserve_when_no_copies_available` |
| R2 | reserve() raises when copies available | ✓ implemented | `catalog/loans.py:55-56`; test `test_reserve_when_copies_available_raises` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/loans.py:50-54`; tests `test_reserve_unknown_member`, `test_reserve_unknown_book` (raise LoanError) |
| R4 | member cannot hold two reservations for same book | ✓ implemented | `catalog/loans.py:57-58` + `store.has_reservation` (`store.py:38`); test `test_cannot_reserve_same_book_twice` |
| R5 | list_reservations() FIFO order | ✓ implemented | `store.get_reservations` preserves append order (`store.py:28-36`), `loans.py:78-81`; test `test_list_reservations_fifo` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:37-46` + `_fulfill_reservation:83-88`; tests `test_return_fulfills_reservation`, `test_return_fulfills_earliest_reservation`, `test_multiple_returns_multiple_fulfillments` |
| R7 | cancel_reservation() removes pending | ✓ implemented | `catalog/loans.py:63-76`; test `test_cancel_reservation` |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `catalog/loans.py:74-75`; test `test_cancel_nonexistent_reservation` |
| R9 | exposed through Catalog facade | ✓ implemented | `catalog/service.py:27-37` (reserve / cancel_reservation / list_reservations) |
| R10 | new tests cover reservation behavior | ✓ implemented | 14 new tests in `tests/test_catalog.py:63-188` (>=3 required) |
| R11 | pre-existing suite passes unchanged | ✓ implemented | no_regression=1.0; seed tests `tests/test_catalog.py:17-57` unmodified |

All requirements satisfied. Layering preserved: models (`Reservation` dataclass) → store (reservation CRUD) → loans (`ReservationError`, reserve/cancel/list/fulfill) → service (facade). `ReservationError` re-exported through `service.py` so the test import `from catalog.service import Catalog, ReservationError` resolves.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 1.0    (build ok + all tests passed — the test gate)
no_regression   = 1.0    (seed suite still green)
defect_rate     = 1.0    (build+test succeeded)
code_quality    = 0.8333 (minor lint)
token_efficiency= 0.0058
```

Skip detection: `grep pytest.skip|mark.skip|xfail tests/` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 381 |
| Files (catalog/ + tests/) | 6 |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| New reservation tests | 14 |
| Agent API calls | 40 |
| Output tokens | 8,713 |

## Findings

Top items (full list in `findings.jsonl`) — no high/critical findings:

1. [info] code_quality=0.833 (minor lint residue), non-blocking
2. [info] reserve()/cancel_reservation() raise LoanError (not ReservationError) for unknown member/book — spec-compliant ("raises an error"), tests assert LoanError

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=beads/rep1
cat scores.json
python -m pytest tests/test_catalog.py -q --tb=short   # 20 passed
grep -rcE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"   # 0
```
