# Evaluation: python · gpt-oss-20b · prompt=neutral · rep 3 (SECOND OPINION)

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (app logic correct; test suite non-functional)
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing — `requirement_coverage = 11/12 = 0.9167`
- **Tests:** 0 passed / 4 failed / 0 skipped (0 effective) — every configuration; see below
- **Build:** pass (imports cleanly under a FastAPI/pydantic-v2 + httpx env)
- **Lint:** code_quality=0.8333 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 low)

## Second-opinion verdict on the prior claim

The first evaluation scored `requirement_coverage=0.9167` and flagged **R12** as unmet
("4 tests exist but none pass; 0 effective passing tests"). **I confirm that factual
claim** and reach the **same 0.9167** score. Three independent lines of evidence:

1. **`.coverage` from the actual scored run** — only import/`def`/decorator lines of the
   tests are recorded (`tests/test_api.py` lines 1-3, 5, 6, 12, 13, 27, 28, 46, 47) and
   **no endpoint body in `app/main.py` ever ran**. The test bodies did not execute.
2. **Reproduction with the run's own files:**
   - no `pytest-asyncio` (the scored env): **4 failed** — "async def functions are not
     natively supported".
   - `pytest-asyncio` + `httpx<0.28`: **1 passed (health), 3 failed** —
     `sqlite3.OperationalError: no such table: books`, because `AsyncClient(app=app)`
     does not trigger the FastAPI `lifespan` that calls `init_db()`.
   - `httpx>=0.28`: **4 failed** — the `app=` shortcut was removed
     (`TypeError: AsyncClient.__init__() got an unexpected keyword argument 'app'`).
   In **no** configuration does the suite go green.
3. **`test_coverage=0.33` is line-coverage, not a pass-rate.** The scorer runs
   `python -m pytest --cov=. --cov-report=term` (`scoring/scorers/test_coverage.py`), so
   0.33 = 33 % of lines executed **at import**, produced even though every test failed.
   The pinned R12 proxy "`test_coverage > 0`" is therefore a false positive here.

**Refinement vs. the first evaluation:** R12 is better classified as **partial**, not
missing — the 4 test functions satisfy the ">= 3 tests exist" half of the deliverable, but
fail the "and run" half. The numerator is 11 either way, so the score is unchanged at
0.9167. The other 11 requirements are genuinely implemented (verified below).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app/main.py` `create_book` — INSERT (title,author,year,isbn), status 201 |
| R2 | GET /books lists all | ✓ implemented | `app/main.py` `list_books` — `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `list_books` — `WHERE author = ?` when query param set |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `get_book` — `SELECT ... WHERE id=?`, raises 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `update_book` — UPDATE, 404 if missing |
| R6 | DELETE /books/{id} | ✓ implemented | `delete_book` — DELETE, 404 if rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3.connect(DATABASE)`, file-backed `books` table via `init_db` |
| R8 | JSON + appropriate status codes | ✓ implemented | `JSONResponse`, 201/200/404/204 across routes |
| R9 | Validation: title & author required | ✓ implemented | `BookBase` `title`/`author` = `Field(...)` → 422 on missing (validation present) |
| R10 | GET /health | ✓ implemented | `health_check` → 200 `{"status":"ok"}` |
| R11 | README with setup & run | ✓ implemented | `README.md` documents venv/install/`uvicorn`/`pytest` (see doc-1 caveat) |
| R12 | At least 3 tests that run | ~ partial | 4 tests defined but **0 pass** in every env; bodies never executed (see above) |

## Build & Test

```text
python -m pytest --cov=. --cov-report=term -q --tb=no   # scored run
test_coverage = 0.33  (33% LINE coverage from import only — every test FAILED)
```

```text
# Reproduction with the run's own tests/, no pytest-asyncio (scored-env equivalent):
4 failed in 0.48s
  test_health / test_create_and_get_book / test_list_and_filter / test_validation_and_update_and_delete
  -> Failed: async def functions are not natively supported
# The application itself is correct: a direct ASGITransport probe (per summary/index.md)
# returns correct status codes for all 8 operations.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 190 |
| Files (source + README) | 4 |
| Dependencies declared | 0 (no requirements.txt/pyproject — see doc-1) |
| Tests total | 4 |
| Tests effective (passed+failed, non-skipped) | 4 |
| Tests passing | 0 |
| Skip ratio | 0% |
| code_quality (scores.json) | 0.8333 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] R12 — "At least 3 tests" partially met: 4 tests exist but 0 pass (async/lifespan/httpx-API breakage)
2. [medium] README references `requirements.txt` that does not exist; deps undeclared
3. [low] DELETE /books/{id} returns 204 with a JSON body (RFC 9110 violation)

## Reproduce

```bash
cd <run_dir>
# Inspect the scored run's coverage (bodies never executed):
python3 - <<'PY'
import sqlite3
c=sqlite3.connect('.coverage')
files={r[0]:r[1] for r in c.execute('SELECT id,path FROM file')}
def bits(b):
    return [i*8+j for i,byte in enumerate(b) for j in range(8) if byte&(1<<j)]
for fid,p in files.items():
    for (nb,) in c.execute('SELECT numbits FROM line_bits WHERE file_id=?',(fid,)):
        print(p.split('/')[-1], bits(nb))
PY

# Reproduce the test outcome (scored-env equivalent, no pytest-asyncio):
mkdir -p /tmp/r12 && cp -r app tests /tmp/r12 && cd /tmp/r12
uv venv -q --python 3.12 && uv pip install -q fastapi "httpx<0.28" pytest anyio
PYTHONPATH=/tmp/r12 uv run pytest -q   # -> 4 failed
```
