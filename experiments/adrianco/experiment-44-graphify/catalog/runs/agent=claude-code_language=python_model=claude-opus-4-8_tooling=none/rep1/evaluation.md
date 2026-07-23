# Evaluation: agent=claude-code language=python model=claude-opus-4-8 tooling=none · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8, agent=claude-code, tooling=none
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — 6 pre-existing + 8 new
- **Build:** pass (import/collection succeeded — test_coverage=0.99 from scores.json)
- **Lint:** pass — code_quality=0.83 from scores.json
- **No-regression:** pass — no_regression=1.0 (original tests/test_catalog.py unchanged and green)
- **Architecture:** run-summary skill unavailable in this session; layering preserved (models / store / loans / reservations / service)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `catalog/REQUIREMENTS.json` (reservations capability only; R11 also gated by the `no_regression` scorer).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records when 0 copies available | ✓ implemented | `reservations.py:20` reserve() appends after availability check; `test_reservations.py:test_reserve_requires_zero_availability` |
| R2 | reserve() raises when copies still available | ✓ implemented | `reservations.py:25` raises if `loans.available(book_id) > 0` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `reservations.py:21-24` member/book None guards; `test_reserve_unknown_member_or_book` |
| R4 | No two reservations by same member for same book | ✓ implemented | `reservations.py:29` duplicate check raises; `test_reserve_duplicate_raises` |
| R5 | list_reservations() is FIFO | ✓ implemented | `reservations.py:49` returns `_for_book` order (append order); `test_reservations_are_fifo` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `service.py:24-27` return_book → pop_next → borrow; availability stays 0; `test_return_fulfills_earliest_reservation` |
| R7 | cancel_reservation removes a pending reservation | ✓ implemented | `reservations.py:39` cancel_reservation removes match; `test_cancel_reservation` |
| R8 | cancel_reservation raises when none exists | ✓ implemented | `reservations.py:45` raises after no match; `test_cancel_reservation` (second cancel) |
| R9 | Exposed through Catalog facade | ✓ implemented | `service.py:33-42` reserve / cancel_reservation / list_reservations methods |
| R10 | New tests cover reservation behavior | ✓ implemented | `tests/test_reservations.py` — 8 tests (≥3 required); test_coverage=0.99 > 0 |
| R11 | Pre-existing suite still passes unchanged | ✓ implemented | no_regression=1.0; 6 tests in `tests/test_catalog.py` unmodified |

## Build & Test

Scores read from `scores.json` (computed during the run's scoring gate — not re-run):

```text
python -m pytest   (via retort scorers)
test_coverage = 0.99   → build/import OK, all tests pass, ~99% line coverage
no_regression = 1.0    → tests/test_catalog.py (6 tests) pass unchanged
defect_rate   = 1.0    → build + test succeeded
code_quality  = 0.8333 → lint/quality gate
```

Skip scan (`grep pytest.skip|@pytest.mark.skip|xfail tests/`): **0 skips** — all tests are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 347 total (190 catalog/, 157 tests/) |
| New code (reservations.py + test_reservations.py) | 159 |
| Files | 8 |
| Dependencies | 0 (stdlib only; pytest for tests) |
| Tests total | 14 (6 existing + 8 new) |
| Tests effective | 14 |
| Skip ratio | 0% |
| test_coverage | 0.99 |

## Findings

Full list in `findings.jsonl` (no findings at or above `low`):

1. [info] test_coverage=0.99, not a perfect 1.0 — one uncovered guard branch
2. [info] Reservation lookups are O(n) linear scans (fine at this scale)

## Reproduce

```bash
cd runs/agent=claude-code_language=python_model=claude-opus-4-8_tooling=none/rep1
cat scores.json                                             # stored mechanical scores
python -m pytest tests/ -q                                  # 14 passed
python -m pytest tests/test_catalog.py -q --tb=short        # no-regression gate (6 passed)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # 0 skips
```
