# Evaluation: agent=claude-code_effort=low_language=python_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, agent=claude-code, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — test_coverage=1.0 from scores.json
- **Build:** pass (test_coverage=1.0 ⇒ imports + tests ran)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:create_book` → `db.create_book`; `test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `main.py:list_books` → `db.list_books`; `test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.list_books(author)` WHERE author=?; `test_list_and_author_filter` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `main.py:get_book` raises 404; `test_missing_book_returns_404` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.py:update_book` → `db.update_book`; `test_update` |
| R6 | DELETE /books/{id} | ✓ implemented | `main.py:delete_book` 204/404; `test_delete` |
| R7 | SQLite storage | ✓ implemented | `db.py` sqlite3 with CREATE TABLE + parameterised SQL |
| R8 | JSON + HTTP status codes | ✓ implemented | 201/200/404/204/422 across routes; response_model=Book |
| R9 | Validation: title/author required | ✓ implemented | `BookIn` Field(min_length=1) + `not_blank` validator; `test_validation_errors` |
| R10 | GET /health | ✓ implemented | `main.py:health` returns `{"status":"ok"}`; `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, tests, endpoints, examples |
| R12 | ≥3 tests | ✓ implemented | 6 test functions, 11 cases via parametrize |

## Build & Test

```text
python -m pytest    (not re-run — using stored scores)
test_coverage=1.0  ⇒ imports succeeded and all tests passed
```

No skipped or disabled tests (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 240 (main 73, db 80, test 87) |
| Files | 12 (incl. archive artifacts) |
| Dependencies | 4 (fastapi, uvicorn, pytest, httpx) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| code_quality | 0.8333 |
| maintainability | 0.9870 |
| idiomatic | 0.75 |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [info] Validation errors return 422 (idiomatic FastAPI), not the 400 the spec loosely implies — acceptable.

## Reproduce

```bash
cd runs/agent=claude-code_effort=low_language=python_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                              # stored mechanical scores
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0
python -m pytest                             # optional re-run: 11 passed
```
