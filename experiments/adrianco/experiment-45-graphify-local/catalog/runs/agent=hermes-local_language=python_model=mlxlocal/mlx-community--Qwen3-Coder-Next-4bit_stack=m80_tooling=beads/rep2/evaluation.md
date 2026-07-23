# Evaluation: hermes-local · python · Qwen3-Coder-Next-4bit · m80 · beads · rep 2

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, stack=m80, tooling=beads
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, task `py-catalog-reservations`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective) — 6 original + 11 new reservation tests
- **Build:** pass — `test_coverage=0.99`, `defect_rate=1.0` from `scores.json` (build+import+tests executed)
- **Lint:** pass — `code_quality=0.833` from `scores.json` (minor deductions, no functional impact)
- **No-regression:** `no_regression=1.0` from `scores.json` (seed suite passes unchanged)
- **Architecture:** `run-summary` skill unavailable in this session — architecture summarized inline below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve records when 0 available | ✓ implemented | `catalog/loans.py:45-64` guards on `available(book_id) > 0`; test `test_reserve_when_no_copies_available` |
| R2 | reserve raises when copies available | ✓ implemented | `catalog/loans.py:54-55` raises `LoanError`; test `test_reserve_when_copies_available_raises` |
| R3 | reserve raises unknown member/book | ✓ implemented | `catalog/loans.py:48-52`; tests `test_reserve_unknown_member_raises`, `test_reserve_unknown_book_raises` |
| R4 | no two reservations same member/book | ✓ implemented | `catalog/loans.py:57-60`; test `test_reserve_duplicate_raises` |
| R5 | list_reservations FIFO | ✓ implemented | `Store._reservations` is an append-ordered `list`, `get_reservations` preserves order (`catalog/store.py:9,32-33`); `catalog/loans.py:76-79`; test `test_list_reservations_fifo` |
| R6 | return_book auto-fulfills earliest | ✓ implemented | `catalog/loans.py:33-43` pops earliest via `pop_earliest_reservation` (first list match = FIFO) and re-issues the loan so availability stays 0; tests `test_return_book_fulfills_reservation`, `..._earliest_reservation_first`, `test_multiple_returns_with_reservations` |
| R7 | cancel_reservation removes pending | ✓ implemented | `catalog/loans.py:66-74` → `catalog/store.py:35-39`; test `test_cancel_reservation` |
| R8 | cancel raises when none | ✓ implemented | `catalog/loans.py:74` raises `LoanError`; test `test_cancel_nonexistent_reservation_raises` |
| R9 | exposed on Catalog facade | ✓ implemented | `catalog/service.py:27-37` — `reserve`, `cancel_reservation`, `list_reservations` |
| R10 | new tests cover reservations | ✓ implemented | 11 new tests (`tests/test_catalog.py:63-161`), well above the ≥3 bar |
| R11 | pre-existing suite passes unchanged | ✓ implemented | `no_regression=1.0`; original 6 tests untouched at `tests/test_catalog.py:17-57` |

Layering preserved (models → store → loans → service): `Reservation` dataclass in `models.py`, storage in `store.py`, logic in `loans.py`, facade in `service.py`. No existing behavior altered.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.99   # build + import + all tests executed and passed (99% line coverage)
defect_rate   = 1.0    # build+test succeeded
no_regression = 1.0    # seed suite passes unchanged
code_quality  = 0.833  # minor lint/style deductions
```

Agent self-report (`_agent_stdout.log`): "All 17 tests pass (6 original + 11 new reservation tests)." Consistent with 17 `def test_` functions and 0 skips grepped from `tests/test_catalog.py`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 352 (catalog/ + tests/) |
| Files (excl. `__pycache__`/`.git`) | 16 |
| Dependencies | 0 (stdlib only; pytest for tests) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| API calls (hermes) | 28 |
| Tokens total | 775,514 (in 53,865 / out 8,945 / cache-read 712,704) |

## Findings

Full list in `findings.jsonl` (2 items, none at or above `high`):

1. [low] code_quality below 1.0 (0.833) — minor lint deductions, no functional impact
2. [info] Redundant existence check in `LoanService.cancel_reservation` (double scan of reservations)

## Reproduce

```bash
cd "runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=beads/rep2"
cat scores.json                                   # stored build/test/lint/regression scores
grep -rEc "^def test_" tests/test_catalog.py      # 17 test functions
grep -rE "pytest\.skip|xfail" tests/ --include="*.py" | wc -l   # 0 skips
python3 -m pytest tests/ -q                        # optional re-verify (test_coverage=0.99 already stored)
```
