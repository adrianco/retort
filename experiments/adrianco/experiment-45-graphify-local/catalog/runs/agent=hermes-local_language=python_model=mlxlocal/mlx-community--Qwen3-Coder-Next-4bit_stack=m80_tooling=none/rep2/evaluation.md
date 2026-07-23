# Evaluation: py-catalog-reservations (m80, tooling=none) · rep 2

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, stack=m80, tooling=none
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass (import/collection succeeded — test_coverage=0.98 from scores.json)
- **Lint:** pass — 1 low-severity dead-code warning
- **Architecture:** layering models/store/loans/service preserved (run-summary skill unavailable in this session — see note below)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist pinned from `REQUIREMENTS.json` (constant denominator = 11).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records reservation when 0 copies available | ✓ implemented | `catalog/loans.py:53-70`; test `test_reserve_unavailable_book` (test_catalog.py:60) |
| R2 | reserve() raises when copies still available | ✓ implemented | `catalog/loans.py:61-62`; test `test_reserve_when_copies_available_raises` (:72) |
| R3 | reserve() raises for unknown member or book | ✓ implemented | `catalog/loans.py:55-60`; tests `test_reserve_unknown_member`/`_book` (:80,:87) |
| R4 | member cannot hold two reservations for same book | ✓ implemented | `catalog/loans.py:64-67`; test `test_reserve_duplicate_raises` (:94) |
| R5 | list_reservations returns members FIFO | ✓ implemented | `catalog/loans.py:81-84` + `store.py:32-33` (append-order filter); test `test_list_reservations_fifo` (:103) |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:42-49`; tests `test_return_book_fulfills_earliest_reservation` (:145), `test_multiple_reservations_multiple_returns` (:159) |
| R7 | cancel_reservation removes a pending reservation | ✓ implemented | `catalog/loans.py:72-78`; test `test_cancel_reservation` (:115) |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `catalog/loans.py:79`; test `test_cancel_reservation_not_found_raises` (:124) |
| R9 | new behavior exposed via Catalog facade | ✓ implemented | `catalog/service.py:27-34` (reserve/cancel_reservation/list_reservations) |
| R10 | new tests cover reservation behavior | ✓ implemented | 12 new tests (test_catalog.py:60-173); ≥3 required |
| R11 | pre-existing suite still passes unchanged | ✓ implemented | original 6 tests retained at test_catalog.py:17-57; no_regression=1.0 from scores.json |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill §2):

```text
{"code_quality": 0.833, "test_coverage": 0.98, "no_regression": 1.0,
 "token_efficiency": 0.0112, "defect_rate": 1.0}
```

- test_coverage=0.98 ⇒ build/import succeeded and tests executed & passed (>0).
- no_regression=1.0 ⇒ seed's original suite passes against the modified tree.
- 18 test functions, 0 skips (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, catalog/) | 189 (loans 84, store 42, service 34, models 28, __init__ 1) |
| Test LOC | 221 |
| Files (source) | 6 |
| Dependencies | 0 (stdlib only — pytest for tests) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] `Store.remove_reservation_by_member_and_book` is unused dead code (`catalog/store.py:38`) — likely the residual test_coverage=0.98.
2. [info] Reservation model + store layer added cleanly, existing layering preserved.

Note: the `run-summary` skill is not available in this session; architecture summary inlined above instead of `summary/index.md`.

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=none/rep2
cat scores.json                                          # stored mechanical scores
grep -rEc "pytest\.skip|xfail" tests/                    # skip count → 0
grep -rn remove_reservation_by_member_and_book catalog/  # dead-code check
# optional re-run: python -m pytest tests/ -q
```
