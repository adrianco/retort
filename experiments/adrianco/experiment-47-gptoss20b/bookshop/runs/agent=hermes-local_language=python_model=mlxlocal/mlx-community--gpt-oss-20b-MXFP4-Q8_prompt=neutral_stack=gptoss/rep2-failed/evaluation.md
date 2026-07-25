# Evaluation: gpt-oss-20b · python · neutral · rep 2 (SECOND OPINION)

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (code runs) — but test gate fails (all tests skipped)
- **Requirements:** 10/12 implemented, 0 partial, 2 missing (R11, R12)
- **Tests:** 0 passed / 0 failed / 2 skipped (0 effective) — `2 skipped, 6 warnings`
- **Build:** pass (imports fine; SQLAlchemy/FastAPI app constructs)
- **Lint:** code_quality=0.7889 (from scores.json)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 2 high, 2 medium, 1 info)

## Second-opinion verdict on the two contested claims

Both claims from the first evaluation are **CONFIRMED**; the first evaluator was correct.

- **R11 (no README):** CONFIRMED missing. `find -iname 'readme*'` over the run_dir returns
  nothing. The full file set is `main.py`, `requirements.txt`, `tests/test_main.py` plus
  harness artifacts — no README in any casing. TASK.md line 19 lists it as a deliverable.
- **R12 (only 2 tests, both skip):** CONFIRMED. `tests/test_main.py` defines exactly 2 test
  functions (`test_health` at :8, `test_crud` at :15). The spec requires ≥3 that run. Both
  are `@pytest.mark.asyncio` but pytest-asyncio is unconfigured (no `asyncio_mode=auto`, no
  conftest/pytest.ini), so the final pytest run reports **`2 skipped, 6 warnings in 0.29s`**
  with *"async def functions are not natively supported and have been skipped"*. The agent's
  own stdout admits: *"tests are skipped due to async plugin not installed."* Effective
  tests = 0, and even the raw count (2) is below the ≥3 threshold. Missing on both grounds.

`requirement_coverage` re-scored over the full checklist = **10/12 = 0.8333** — unchanged
from the first evaluation.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:73` create_book, BookCreate(title/author/year/isbn), db.add+commit |
| R2 | GET /books lists all | ✓ implemented | `main.py:82` list_books returns query.all() |
| R3 | ?author= filter | ✓ implemented | `main.py:84,88-89` filter(BookORM.author==author) |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `main.py:94-99` 404 raised when not found |
| R5 | PUT /books/{id} | ✓ implemented | `main.py:102` update_book, setattr loop + commit |
| R6 | DELETE /books/{id} | ✓ implemented | `main.py:115` delete_book, 204 response |
| R7 | SQLite storage | ✓ implemented | `main.py:15` sqlite:///./books.db via SQLAlchemy |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/204 across routes |
| R9 | title & author required | ✓ implemented | `main.py:36-37` Field(...,min_length=1) → 422 reject (spec says 400; 422 is FastAPI idiom) |
| R10 | GET /health | ✓ implemented | `main.py:68` health_check → {"status":"ok"} |
| R11 | README.md setup/run | ✗ missing | no README file in run_dir |
| R12 | ≥3 tests that run | ✗ missing | 2 tests defined, both skipped → 0 effective |

## Build & Test

```text
pytest tests/
2 skipped, 6 warnings in 0.29s
  async def functions are not natively supported and have been skipped.
```

Stored mechanical scores (`scores.json`): test_coverage=0.51, code_quality=0.7889,
defect_rate=1.0, maintainability=0.5826, idiomatic=0.72. (The 0.51 is a coverage fraction,
not a pass-rate; no test actually executed — both were skipped.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | 168 (main.py 126 + tests 42) |
| Files (source) | 3 |
| Dependencies | 7 |
| Tests total | 2 |
| Tests effective | 0 |
| Skip ratio | 100% |

## Findings

1. [high] R11 — No README.md with setup/run instructions
2. [high] R12 — Fewer than 3 running tests (2 defined, both skipped → 0 effective)
3. [medium] test_health skipped (async plugin not active)
4. [medium] test_crud skipped (async plugin not active)
5. [info] R9 validation returns 422 vs spec's 400 (FastAPI idiom, acceptable)

## Reproduce

```bash
cd "<run_dir>"
find . -iname 'readme*'                 # empty → R11 missing
grep -c 'def test_' tests/test_main.py  # 2 → below ≥3
python -m pytest tests/                 # 2 skipped, 6 warnings
```
