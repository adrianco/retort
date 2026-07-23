# Evaluation: agent=claude-code language=python model=claude-opus-4-8 tooling=beads · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8, agent=claude-code, tooling=beads
- **Status:** ok
- **Requirements:** 11/11 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — 6 existing + 9 new
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.83 from scores.json (no specific warnings surfaced)
- **Architecture:** run-summary skill not available in this session — see file walk below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `experiment-44-graphify/catalog/REQUIREMENTS.json` (constant denominator = 11).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | reserve() records when 0 copies available | ✓ implemented | `catalog/reservations.py:27-42`; test `test_reserve_requires_zero_availability` |
| R2 | reserve() raises when copies still available | ✓ implemented | `catalog/reservations.py:32-35`; same test asserts raise |
| R3 | reserve() raises for unknown member/book | ✓ implemented | `catalog/reservations.py:28-31`; test `test_reserve_unknown_member_or_book` |
| R4 | No two reservations by same member/book | ✓ implemented | `catalog/reservations.py:36-39`; test `test_reserve_duplicate_raises` |
| R5 | list_reservations() FIFO order | ✓ implemented | `catalog/reservations.py:52-53`; test `test_reservations_are_fifo` |
| R6 | return_book auto-fulfills earliest reservation | ✓ implemented | `catalog/service.py:23-29` + `pop_earliest` `reservations.py:55-62`; test `test_return_fulfills_earliest_reservation` |
| R7 | cancel_reservation removes pending reservation | ✓ implemented | `catalog/reservations.py:44-50`; test `test_cancel_reservation` |
| R8 | cancel_reservation raises when none | ✓ implemented | `catalog/reservations.py:46-49`; test `test_cancel_without_reservation_raises` |
| R9 | Exposed through Catalog facade | ✓ implemented | `catalog/service.py:34-41` (reserve/cancel_reservation/list_reservations) |
| R10 | ≥3 new tests cover reservation behavior | ✓ implemented | `tests/test_reservations.py` — 9 new tests |
| R11 | Existing test_catalog.py still passes | ✓ implemented | no_regression=1.0 (scores.json); 6 existing tests unchanged |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage:   0.99   (build + all tests pass; ~1 uncovered line)
no_regression:   1.0    (original tests/test_catalog.py suite passes unchanged)
defect_rate:     1.0    (build + test succeeded)
code_quality:    0.833
token_efficiency:0.0109
```

Agent self-report (`_agent_stdout.log`): "15/15 tests pass — the 6 existing tests ... are unchanged and still pass."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 369 |
| Files (catalog/ + tests/) | 8 |
| Tests total | 15 (6 existing + 9 new) |
| Tests effective | 15 |
| Skip ratio | 0% |
| New reservation tests | 9 |

## Findings

Full list in `findings.jsonl` (both info-level — the run has no correctness defects):

1. [info] tooling=beads did not take effect — `bd` was uninstallable, agent fell back to the harness task tracker (no `.beads/` dir). Relevant to the experiment's tooling factor per CLAUDE.md's verify-before-run principle.
2. [info] test_coverage=0.99 — one uncovered line (likely the empty-reservations `pop_earliest` return path); behavior is exercised indirectly.

## Reproduce

```bash
cd runs/agent=claude-code_language=python_model=claude-opus-4-8_tooling=beads/rep1
cat scores.json                          # stored mechanical scores
python -m pytest tests/ -q               # 15 passed (build+test signal already in scores.json)
grep -rE "pytest\.skip|xfail" tests/     # 0 skips
```
