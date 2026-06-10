# Evaluation: language=python_model=claude-fable-5 · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (build+tests succeeded)
- **Lint:** moderate — code_quality=0.6222 from scores.json
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:92-108` create_book() accepts all four fields, inserts into SQLite |
| R2 | GET /books lists all books | ✓ implemented | `app.py:110-120` list_books() returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:112-118` filters by author query param |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `app.py:122-126` get_book() returns one book, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:128-152` update_book() with partial update support |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:154-161` delete_book() removes book, 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4,27,38` uses sqlite3.connect() with file-backed DB |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | Routes use jsonify() with 201/200/400/404/204 codes |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:50-86` validate_payload() rejects missing/empty title and author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:88-90` returns {"status": "ok"} |
| R11 | README.md with setup and run instructions | ✓ implemented | README.md has setup (pip install), run (python app.py), test instructions, endpoint table |
| R12 | At least 3 unit/integration tests | ✓ implemented | test_app.py has 7 test functions: health, create, validation, list+filter, get, update, delete |

## Build & Test

```text
Build+test status from scores.json (retort scorers already ran):
  test_coverage = 1.0  → all tests passed
  defect_rate   = 1.0  → build+test succeeded
  code_quality  = 0.6222
  maintainability = 1.0
  idiomatic     = 0.72
```

```text
Test functions (7 total, 0 skipped):
  test_health
  test_create_book
  test_create_book_validation
  test_list_books_and_author_filter
  test_get_single_book
  test_update_book
  test_delete_book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 290 (175 app.py + 115 test_app.py) |
| Files | 9 |
| Dependencies | 2 (flask>=3.0, pytest>=8.0) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (from stored scores) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] Moderate code quality score from linter — code_quality=0.6222
2. [low] No type annotations on any functions
3. [low] Idiomatic score below threshold — idiomatic=0.72

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=python_model=claude-fable-5/rep2
cat scores.json                          # stored build/test/lint scores
cat TASK.md                              # task spec
cat stack.json                           # factor levels
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py"  # skipped tests
find . -name "*.py" -not -path "*/__pycache__/*" | xargs wc -l     # lines of code
```
