# Evaluation: agent=hermes-local_language=python_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R9 has a low-severity gap on empty-string validation)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — from `test_coverage=0.98` (retort.db/scores.json; 1.0 gate ⇒ build+tests ran)
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** trivial 2-file Flask app; `run-summary` skill not invoked (not warranted for a single-module codebase)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_api/book_api/app.py:27` create_book; INSERT at :36 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:44` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:50` `WHERE author = ?`; tested `test_app.py:61` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:64` get_book; 404 at :72 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:82` update_book; 404 at :95 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:100` delete_book; 404 at :106 |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:10` sqlite3.connect(DATABASE); books.db present |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/204/400 across routes |
| R9 | Validation: title & author required | ✓ implemented | `app.py:30` (key-presence only; empty strings accepted — see findings) |
| R10 | GET /health | ✓ implemented | `app.py:23` health_check → 200 |
| R11 | README with setup/run | ✓ implemented | `book_api/book_api/README.md` |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 tests in `test_app.py` |

## Build & Test

```text
Scores read from scores.json (no re-run per evaluate-run skill):
test_coverage = 0.98   → build succeeded, all tests executed and passed
defect_rate   = 1.0    → build+test success
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.8
```

```text
6 tests, 0 skipped: test_health_check, test_create_book, test_list_books,
test_get_book, test_update_book, test_delete_book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 253 (app.py 113 + test_app.py 140) |
| Files (app + tests + README + reqs) | 4 |
| Dependencies | 1 (flask) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — validation checks key presence, not empty/whitespace values (`app.py:30`)
2. [info] Redundant nested directory `book_api/book_api/`
3. [info] POST echoes raw request body including unexpected fields (`app.py:42`)

No critical/high/medium findings. This run cleanly implements the full spec.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-23-devstral/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep3
cat scores.json
cd book_api/book_api && python -m pytest test_app.py -v
```
