# Evaluation: py-catalog-reservations · rep 1

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, tooling=none, stack=m80
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective; 6 seed + 11 new)
- **Build:** pass — `test_coverage=0.99` from `scores.json` (import + collection succeeded, all tests ran)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **No-regression:** pass — `no_regression=1.0` from `scores.json`
- **Architecture:** run-summary not generated (optional step skipped; codebase is 5 small modules, described below)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

Pinned list from `catalog/REQUIREMENTS.json` (reservations capability only; R11 is the no-regression gate).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records when 0 copies available | ✓ implemented | `catalog/loans.py:53-69`; `tests/test_catalog.py:test_reserve_when_unavailable` |
| R2 | reserve() raises when copies available | ✓ implemented | `catalog/loans.py:61-62`; `test_reserve_when_available_raises` |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/loans.py:55-59`; `test_reserve_unknown_member`, `test_reserve_unknown_book` |
| R4 | No two reservations same member+book | ✓ implemented | `catalog/loans.py:64-66`; `test_reserve_duplicate_raises` |
| R5 | list_reservations() FIFO order | ✓ implemented | `catalog/loans.py:78-81` + `store.py:32-33` (insertion order); `test_list_reservations_fifo` |
| R6 | return_book auto-fulfills earliest | ✓ implemented | `catalog/loans.py:42-49` (fulfills `reservations[0]`, availability stays 0); `test_return_book_fulfills_reservation`, `test_multiple_reservations_fulfilled_on_return` |
| R7 | cancel_reservation removes pending | ✓ implemented | `catalog/loans.py:71-76`; `test_cancel_reservation` |
| R8 | cancel_reservation raises when none | ✓ implemented | `catalog/loans.py:73-75`; `test_cancel_nonexistent_reservation` |
| R9 | Exposed via Catalog facade | ✓ implemented | `catalog/service.py:27-37` (reserve / cancel_reservation / list_reservations) |
| R10 | New tests cover reservations | ✓ implemented | 11 new tests `tests/test_catalog.py:64-183` (≥3 required) |
| R11 | Pre-existing suite still passes | ✓ implemented | `no_regression=1.0`; original 6 tests unchanged and green |

Layering preserved: `Reservation` dataclass in `models.py`, persistence in `store.py` (`add/get/remove/get_reservation`), logic in `loans.py`, facade in `service.py` — matches the task's constraint to keep the models/store/loans/service split.

## Build & Test

Scores read from `scores.json` (no re-run per evaluate-run skill):

```text
test_coverage   = 0.99   (import + collection ok, all tests executed)
no_regression   = 1.0    (seed suite tests/test_catalog.py pass unchanged)
code_quality    = 0.8333
defect_rate     = 1.0
token_efficiency= 0.0138
```

Agent self-report (`_agent_stdout.log`): "All 17 tests pass." Consistent with stored scores.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 189 (`catalog/*.py`) |
| Test LOC | 182 (`tests/test_catalog.py`) |
| Files (source) | 5 |
| Tests total | 17 (6 seed + 11 new) |
| Tests effective | 17 |
| Skip ratio | 0% |
| API calls | 17 |
| Total tokens | 405,411 (6,541 output) |

## Findings

No correctness, build, test, or requirement defects. Full list in `findings.jsonl`:

1. [info] Low token efficiency (0.0138) — 405k total tokens for a small modification. Informational, not a defect.

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_stack=m80_tooling=none/rep1
cat scores.json                     # stored mechanical scores (no re-run)
grep -cE "^def test_" tests/test_catalog.py   # 17
grep -rE "pytest\.skip|xfail" tests/          # 0 skips
python -m pytest tests/test_catalog.py -q      # optional: confirms 17 passed
```
