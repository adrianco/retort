# Evaluation: gptoss / python / hermes-local · rep 3 (SECOND OPINION)

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** failed (0 of 4 tests pass — the async test harness never runs the test bodies)
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing → requirement_coverage = **0.9167**
- **Tests:** 0 passed / 4 failed / 0 skipped (4 effective, all failing)
- **Build:** pass (module imports; app is well-formed)
- **Lint:** minor — 2 low-severity idiom/compliance nits
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 2 high, 1 medium, 2 low)

## Second-opinion verdict

The first evaluation scored **requirement_coverage=0.9167** and claimed **R12 was NOT met**
(4 tests exist, 0 pass). **This re-check CONFIRMS the first evaluator was correct.** I went
and looked:

- **R12 is genuinely unmet.** I reproduced the exact scoring command
  (`python -m pytest --cov=. --cov-report=term`) on an isolated copy. Result:
  `4 failed, 10 warnings` — **0 passed**. Every test fails with
  `Failed: async def functions are not natively supported`, because the tests are decorated
  `@pytest.mark.asyncio` (tests/test_api.py:5,12,27,46) but **pytest-asyncio is not declared
  or installed** — there is no `requirements.txt` at all.
- **The 0.33 does NOT mean tests passed.** `scores.json` `test_coverage=0.33` is the line-
  coverage **percentage** taken from the pytest-cov `TOTAL` line
  (`src/retort/scoring/scorers/test_coverage.py:774-787` parses coverage% *before* any pass-
  rate fallback). My reproduced run's `TOTAL … 33%` matches it exactly. Independently, the
  archived `.coverage` numbits show only module-level `def`/decorator/import lines were
  executed in both `app/main.py` and `tests/test_api.py` — **no endpoint or test body ever
  ran**. So 33% is import-only coverage, not evidence of passing tests, exactly as the first
  evaluator stated.

The first evaluator's evidence pointer (`test-fail-1`, `test_coverage=0.33` reflecting
import-only coverage) is accurate. No implementation was missed. R12 stays **partial** (tests
written but non-functional), and **requirement_coverage remains 11/12 = 0.9167**.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app/main.py:59-70` create_book, INSERT with 4 fields |
| R2 | GET /books lists all | ✓ implemented | `app/main.py:72-82` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app/main.py:73,76-77` WHERE author=? |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app/main.py:84-93` get_book, 404 on None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app/main.py:95-109` update_book, 404 if missing |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app/main.py:111-121` delete_book, 404 if rowcount 0 (204 body nit) |
| R7 | SQLite persistence | ✓ implemented | `app/main.py:4,12-32` sqlite3 + books table |
| R8 | JSON + correct status codes | ✓ implemented | 201/404/204/422 across routes |
| R9 | Validation: title/author required | ✓ implemented | `app/main.py:44-45` Field(...) required → 422 |
| R10 | GET /health | ✓ implemented | `app/main.py:124-126` returns {"status":"ok"} 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup + uvicorn run + pytest |
| R12 | >=3 tests run and pass | ~ **partial** | 4 tests in `tests/test_api.py` but **0 pass** — async harness not wired (reproduced: 4 failed) |

## Build & Test

```text
python -m pytest --cov=. --cov-report=term        # reproduced on isolated copy
FAILED tests/test_api.py::test_health - Failed: async def functions are not natively supported
FAILED tests/test_api.py::test_create_and_get_book - Failed: async def functions ...
FAILED tests/test_api.py::test_list_and_filter - Failed: async def functions ...
FAILED tests/test_api.py::test_validation_and_update_and_delete - Failed: async ...
TOTAL                 138     92    33%
======================== 4 failed, 10 warnings in 0.57s ========================
```

Root cause: `@pytest.mark.asyncio` is used but `pytest-asyncio` is absent (no
`requirements.txt`), so pytest treats the async tests as unsupported and fails all four
without running their bodies.

## Metrics

| Metric | Value |
|--------|-------|
| Lines (source, app+tests) | ~190 total (main.py 126, test_api.py ~64) |
| Files (source) | 3 |
| Declared dependencies | 0 (no requirements.txt/pyproject.toml) |
| Tests total | 4 |
| Tests effective (pass+fail) | 4 (0 pass / 4 fail) |
| Skip ratio | 0% |
| Coverage (import-only) | 33% |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [high] test-fail-1 — all 4 tests fail ("async def not natively supported"); pytest-asyncio missing
2. [high] R12 — ">=3 tests run and pass" unmet: 4 exist, 0 pass
3. [medium] dep-manifest — no requirements.txt; deps (fastapi/httpx/pytest-asyncio) undeclared
4. [low] delete-204-body — DELETE returns a body with 204 No Content
5. [low] pydantic-v1-idioms — orm_mode / Field(example=) deprecated under pydantic v2

## Reproduce

```bash
cd <run_dir>
# isolated copy so run_dir is not mutated:
cp -r app tests README.md /tmp/rep3copy && cd /tmp/rep3copy
python -m pytest --cov=. --cov-report=term        # -> 4 failed, TOTAL 33%
# inspect archived coverage (only def lines covered => bodies never ran):
python3 - <<'PY'
import sqlite3
def nums(nb):
    return [i*8+b for i,byte in enumerate(nb) for b in range(8) if byte&(1<<b)]
c=sqlite3.connect('<run_dir>/.coverage')
for fid,p in c.execute('SELECT id,path FROM file'):
    nb=c.execute('SELECT numbits FROM line_bits WHERE file_id=?',(fid,)).fetchone()[0]
    print(p.split('/rep3/')[1], nums(nb))
PY
```
