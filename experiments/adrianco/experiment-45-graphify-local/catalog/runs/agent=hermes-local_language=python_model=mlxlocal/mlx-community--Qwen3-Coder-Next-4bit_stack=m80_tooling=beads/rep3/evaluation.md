# Evaluation: python · mlxlocal/Qwen3-Coder-Next-4bit · beads · m80 · rep 3

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, tooling=beads, stack=m80
- **Status:** ok — clean pass
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `catalog/REQUIREMENTS.json`)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective) — 6 pre-existing + 14 new reservation tests
- **Build:** pass — `defect_rate=1.0` (scores.json)
- **Test:** pass — `test_coverage=0.99`, `no_regression=1.0` (scores.json); DB row absent (inline eval)
- **Lint:** pass — `code_quality=0.8333` (scores.json); minor import-ordering nits only
- **Architecture:** run-summary skill not available in this session — layering assessed inline (see below)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `catalog/REQUIREMENTS.json` (the NEW reservations capability; the seed suite is separately gated by `no_regression`).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records reservation when 0 copies available | ✓ implemented | `catalog/loans.py:53-66`; test `test_reserve_unavailable_book` |
| R2 | reserve() raises when copies still available | ✓ implemented | `catalog/loans.py:58-59`; test `test_reserve_available_book_raises` |
| R3 | reserve() raises for unknown member or book | ✓ implemented | `catalog/loans.py:54-57`; tests `test_reserve_unknown_member_raises`, `test_reserve_unknown_book_raises` |
| R4 | member cannot hold two reservations for same book | ✓ implemented | `catalog/loans.py:61-63`; test `test_reserve_duplicate_raises` |
| R5 | list_reservations() returns members in FIFO order | ✓ implemented | `catalog/loans.py:79-83`, `store.py:28-36` (append + ordered filter); tests `test_list_reservations`, `test_reservation_fifo_order` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/loans.py:41-49`; tests `test_reservation_fulfilled_on_return`, `test_reservation_fifo_order`, `test_multiple_copies_with_reservations` |
| R7 | cancel_reservation() removes a pending reservation | ✓ implemented | `catalog/loans.py:68-77`; test `test_cancel_reservation` |
| R8 | cancel_reservation raises when member has none | ✓ implemented | `catalog/loans.py:75-76`; test `test_cancel_reservation_not_found_raises` |
| R9 | new behavior exposed on Catalog facade | ✓ implemented | `catalog/service.py:27-34` (reserve / cancel_reservation / list_reservations) |
| R10 | new tests cover reservation behavior | ✓ implemented | `tests/test_catalog.py:61-208` — 14 new tests; `test_coverage=0.99` |
| R11 | pre-existing suite still passes unchanged | ✓ implemented | `no_regression=1.0`; original 6 tests unmodified (`tests/test_catalog.py:18-58`) |

## Build & Test

Scores read from `scores.json` (inline eval — no `retort.db` row yet); toolchain not re-run per skill guidance.

```text
python -m pytest tests/test_catalog.py -q --tb=short   # regression command from .retort-regression.json
test_coverage=0.99  no_regression=1.0  defect_rate=1.0   → 20 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 389 |
| Files (.py) | 6 |
| Dependencies | pytest (stdlib + pytest only) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build/test | pass |

## Findings

No critical/high/medium/low findings. Two info-level observations (full list in `findings.jsonl`):

1. [info] `reserve()` permits a current borrower to also reserve the same book — allowed by the spec (only two reservations by the same member are prohibited); noted as a design permissiveness, not a defect. `catalog/loans.py:53-66`
2. [info] Non-alphabetical import ordering in `service.py`/`loans.py` — cosmetic; likely the source of `code_quality=0.8333`.

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=beads/rep3
cat scores.json                                   # stored mechanical scores
python -m pytest tests/test_catalog.py -q --tb=short   # regression command (do not re-run during eval)
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # → 0 skips
```
