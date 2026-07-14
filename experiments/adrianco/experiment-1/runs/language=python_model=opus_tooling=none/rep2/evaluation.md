# Evaluation: language=python_model=opus_tooling=none · rep 2

## Summary

- **Factors:** language=python, model=opus, tooling=none
- **Status:** failed (test gate: test_coverage=0.0 — tests did not execute)
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — tests did not execute
- **Build:** fail — test_coverage=0.0 from retort.db (build or import failure)
- **Lint:** unavailable — code_quality=0.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (1 critical, 0 high, 1 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `app.py:68-77` — `@app.post("/books", status_code=201)` with BookIn(title, author, year, isbn) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:79-88` — `@app.get("/books")` returns full list |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:80` — `author: Optional[str] = Query(None)`, filters at lines 82-86 |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:90-95` — returns book or 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:98-111` — updates all fields, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:113-122` — `status_code=204`, 404 if absent |
| R7 | SQLite storage | ✓ implemented | `app.py:1,10-26` — imports sqlite3, creates books table |
| R8 | JSON + HTTP status codes | ✓ implemented | `app.py:68` (201), `app.py:113` (204), `app.py:95,105,120` (404) |
| R9 | Validation: title+author required | ✓ implemented | `app.py:40-41` — `Field(..., min_length=1)` on both |
| R10 | GET /health endpoint | ✓ implemented | `app.py:64-65` — returns `{"status": "ok"}` |
| R11 | README with instructions | ✓ implemented | `README.md` — setup (pip install) and run (uvicorn) documented |
| R12 | At least 3 tests | ~ partial | `test_app.py` has 6 test functions but test_coverage=0.0 (tests did not execute) |

## Build & Test

```text
Build/test scores from retort.db (not re-run per skill policy):
  test_coverage  = 0.0  (tests did not execute)
  code_quality   = 0.0
  defect_rate    = 0.0
  maintainability= 0.0
  idiomatic      = 0.0
  token_efficiency=0.0
```

```text
Tests defined in test_app.py (6 functions):
  test_health
  test_create_and_get_book
  test_create_validation
  test_list_and_filter
  test_update_and_delete
  test_not_found

None executed (test_coverage=0.0 — likely build/import failure in test environment).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 211 (app.py: 127, test_app.py: 84) |
| Files | 6 |
| Dependencies | 5 (fastapi, uvicorn, pydantic, httpx, pytest) |
| Tests total | 6 |
| Tests effective | 0 |
| Skip ratio | 0% |
| Build duration | N/A (scores from DB) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. **[critical]** Test gate failed: test_coverage=0.0 (tests did not execute)
2. **[medium]** Tests exist (6 functions) but did not execute (test_coverage=0.0)

## Reproduce

```bash
cd experiment-1/runs/language=python_model=opus_tooling=none/rep2
cat stack.json
cat TASK.md
# Scores were read from retort.db — no build/test re-run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='python' AND json_extract(er.run_config_json,'\$.model')='opus' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -cE "^def test_" test_app.py
```
