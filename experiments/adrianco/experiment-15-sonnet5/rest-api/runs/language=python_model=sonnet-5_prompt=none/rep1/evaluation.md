# Evaluation: language=python model=sonnet-5 prompt=none · rep 1

## Summary

- **Factors:** language=python, model=sonnet-5, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — (test_coverage=1.0 from scores.json; build+tests executed by scorer)
- **Lint:** pass — code_quality=0.833 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:58 create_book` → `database.py:30 create_book` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `main.py:63 list_books` → `database.py:42` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:65` Query param → `database.py:45` WHERE author LIKE; `test_main.py:54` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.py:70 get_book`, 404 on absent (`main.py:73-74`); `test_main.py:41` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.py:78 update_book` → `database.py:60`; 404 on absent; `test_main.py:69` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `main.py:90 delete_book` → `database.py:73`; 204/404; `test_main.py:88` |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:9-27` raw sqlite3 + CREATE TABLE books |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/404/422 via response_model + HTTPException |
| R9 | Validation: title & author required | ✓ implemented | `main.py:27-38` min_length + not_blank validator; `test_main.py:46` (422, see finding) |
| R10 | GET /health | ✓ implemented | `main.py:53 health` → `{"status":"ok"}`; `test_main.py:23` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run (uvicorn), tests, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 9 tests in `test_main.py`; test_coverage=1.0 |

## Build & Test

Build/test not re-run — stored scorer results used (per skill Step 2):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
  → build succeeded and all tests passed (test gate = 1.0)
```

```text
pytest (per agent stdout / grep): 9 tests, 0 skipped, 0 xfail
  test_health_check, test_create_and_get_book, test_get_book_not_found,
  test_create_book_missing_required_fields, test_list_books_with_author_filter,
  test_update_book, test_update_book_not_found, test_delete_book, test_delete_book_not_found
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 269 (main 94 / database 76 / test 99) |
| Files (excl. venv) | 13 (5 primary: 3 .py + README + requirements) |
| Dependencies | 5 (fastapi, uvicorn, pydantic, pytest, httpx) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

Other scorer metrics: token_efficiency=1.0, maintainability=0.268, idiomatic=0.2.

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Missing-field validation rejects with 422, not the 400 referenced in R9's verification note (idiomatic FastAPI; requirement still satisfied).
2. [low] sqlite3 connections committed via `with` but never explicitly closed — relies on refcount GC (`database.py`).
3. [info] `?author=` filter uses substring `LIKE %author%` match rather than exact match.

No critical, high, or medium findings. All 12 requirements implemented; tests pass with zero skips.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=python_model=sonnet-5_prompt=none/rep1
cat scores.json                      # stored build/test/lint scores (no re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py"   # 0
grep -cE "^def test_" test_main.py   # 9
# optional live re-run:
source venv/bin/activate && pytest -q
```
