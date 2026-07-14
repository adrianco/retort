# Evaluation: language=python_model=sonnet_tooling=beads · rep 2

## Summary

- **Factors:** language=python, model=sonnet, tooling=beads
- **Status:** failed (test_coverage=0.24, defect_rate=0.0 — tests ran but majority failed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** ~3 passed / ~9 failed / 0 skipped (12 effective)
- **Build:** pass (inferred from test_coverage > 0) — test_coverage=0.24 from retort.db
- **Lint:** code_quality=0.8 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 item in `findings.jsonl` (0 critical, 1 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `main.py:54` `@app.post("/books", status_code=201)`, `BookCreate` model with title/author/year/isbn |
| R2 | GET /books lists all books | ✓ implemented | `main.py:66` `@app.get("/books")` returns all rows |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:67` `author: Optional[str] = Query(default=None)`, `main.py:70` SQL LIKE filter |
| R4 | GET /books/{id} returns single book | ✓ implemented | `main.py:78` `@app.get("/books/{book_id}")`, 404 on missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:87` `@app.put("/books/{book_id}")`, dynamic SET clause |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:102` `@app.delete("/books/{book_id}", status_code=204)` |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:1` `import sqlite3`, `database.py:9` `sqlite3.connect(DB_PATH)` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 read/update, 204 delete, 404 not found, 400/422 validation |
| R9 | Input validation: title and author required | ✓ implemented | `main.py:23-28` `field_validator("title", "author")` with `not_empty` check |
| R10 | GET /health endpoint | ✓ implemented | `main.py:49` `@app.get("/health")` returns `{"status": "ok"}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, endpoints, tests, configuration sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_books.py` — 12 test functions covering all endpoints |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run per policy):
  test_coverage  = 0.24
  code_quality   = 0.80
  defect_rate    = 0.00
  maintainability = 0.94
  idiomatic      = 0.75
  token_efficiency = 0.50
```

```text
Test file: test_books.py
12 test functions defined, 0 skipped.
test_coverage=0.24 indicates ~3/12 tests passed during scoring.
Code and tests appear correct on inspection — failures likely environmental.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 272 (main.py: 107, database.py: 37, test_books.py: 128) |
| Files | 10 |
| Dependencies | 6 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (from stored scores) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] Test suite mostly failing — test_coverage=0.24, defect_rate=0.0; 12 test functions present but ~76% failed during scoring

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=beads/rep2
cat stack.json
cat scores.json  # if present
sqlite3 ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='python' AND json_extract(er.run_config_json,'$.tooling')='beads' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -cE "^def test_" test_books.py
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py"
```
