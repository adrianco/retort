# Evaluation: language=python_model=opus_tooling=none · rep 3

## Summary

- **Factors:** language=python, model=opus, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=0.94 from retort.db
- **Lint:** pass — code_quality=0.9556 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `app.py:65-84` create_book route accepts title, author, year, isbn |
| R2 | GET /books lists all books | ✓ implemented | `app.py:86-96` list_books route returns collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:88-94` filters by author query param |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:98-104` get_book route, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:106-129` update_book route modifies existing book |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:131-139` delete_book route, 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:2` imports sqlite3, `app.py:16-29` init_db creates table |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | Uses jsonify with 200/201/204/400/404 throughout |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:70-73` validates title, `app.py:72-73` validates author on create; also validated on update |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:61-63` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents setup (pip install), run (python app.py), endpoints, and tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` contains 6 tests, all passing |

## Build & Test

```text
test_coverage=0.94 from retort.db (build + all tests passed)
code_quality=0.9556 from retort.db
defect_rate=0.7826 from retort.db
```

```text
test session starts
platform linux -- Python 3.12.1, pytest-8.3.3, pluggy-1.6.0
collected 6 items

test_app.py ......                                                       [100%]

============================== 6 passed in 0.20s ===============================
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 224 (145 app.py + 79 test_app.py) |
| Files | 7 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | stored score (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Partial update support on PUT — enhancement beyond spec

## Reproduce

```bash
cd experiment-1/runs/language=python_model=opus_tooling=none/rep3
cat scores.json 2>/dev/null || echo "scores.json absent; scores from retort.db"
cat test_output.txt
grep -rE "pytest.skip|@pytest.mark.skip|xfail" --include="*.py" | wc -l
find . -type f -name "*.py" -not -path "*/__pycache__/*" -exec wc -l {} +
```
