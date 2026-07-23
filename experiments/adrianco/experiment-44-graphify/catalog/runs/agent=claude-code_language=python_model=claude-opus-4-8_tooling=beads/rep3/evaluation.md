# Evaluation: agent=claude-code language=python model=claude-opus-4-8 tooling=beads · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8, agent=claude-code, tooling=beads
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — 6 original + 10 new
- **Build:** pass (import/collection succeeded) — `test_coverage=0.99` from `scores.json`
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **No-regression:** pass — `no_regression=1.0` (original `tests/test_catalog.py` unchanged & green)
- **Architecture:** run-summary skill not available; small library summarized inline below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

Pinned checklist from `catalog/REQUIREMENTS.json` (11 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve records when 0 available | ✓ implemented | `catalog/reservations.py:27-42`; test `test_reserve_requires_zero_availability` |
| R2 | reserve raises when copies available | ✓ implemented | `catalog/reservations.py:32-35` (`available>0` → raise) |
| R3 | reserve raises for unknown member/book | ✓ implemented | `catalog/reservations.py:28-31`; test `test_reserve_unknown_member_or_book` |
| R4 | no two reservations by same member/book | ✓ implemented | `catalog/reservations.py:36-39`; test `test_no_duplicate_reservation` |
| R5 | list_reservations FIFO | ✓ implemented | `catalog/reservations.py:52-54`; test `test_reservations_are_fifo` |
| R6 | return_book auto-fulfills earliest | ✓ implemented | `catalog/service.py:23-26` + `reservations.py:56-66`; test `test_return_fulfills_earliest_reservation` |
| R7 | cancel_reservation removes pending | ✓ implemented | `catalog/reservations.py:44-50`; test `test_cancel_reservation` |
| R8 | cancel raises when none | ✓ implemented | `catalog/reservations.py:45-49`; test `test_cancel_missing_reservation_raises` |
| R9 | exposed via Catalog facade | ✓ implemented | `catalog/service.py:31-38` (reserve/cancel_reservation/list_reservations) |
| R10 | new tests cover reservations | ✓ implemented | `tests/test_reservations.py` — 10 tests (>=3 required) |
| R11 | pre-existing suite still passes | ✓ implemented | `no_regression=1.0`; `tests/test_catalog.py` untouched (6 tests) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
{"code_quality": 0.8333, "test_coverage": 0.99, "no_regression": 1.0,
 "token_efficiency": 0.0089, "defect_rate": 1.0}
```

Agent's own final run: `python3 -m pytest -q` → 16 tests pass (6 original + 10 new). No skips/xfail (`grep` count = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `catalog/`) | 196 |
| Files (catalog/ + tests/) | 8 |
| Dependencies | 0 (stdlib only) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build/test signal | test_coverage=0.99 |

## Architecture

Clean adherence to the seed's models/store/loans/service layering. The new
`ReservationService` (`catalog/reservations.py`) is a peer to `LoanService`,
holding an ordered `list[Reservation]` (FIFO by append order). `Catalog`
(`service.py`) composes it and calls `reservations.fulfill_next(book_id)` after
`return_book`, which pops the earliest reserver and immediately re-borrows the
freed copy so availability stays 0. No existing loan logic was modified.

## Findings

Only observation (does not affect code correctness):

1. [info] beads (`bd`) not installed; agent fell back to built-in Task tools — the `tooling=beads` factor did not take effect on this runner.

## Reproduce

```bash
cd runs/agent=claude-code_language=python_model=claude-opus-4-8_tooling=beads/rep3
cat scores.json                      # stored mechanical scores
python3 -m pytest -q                 # 16 passed
grep -rE "pytest\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
```
