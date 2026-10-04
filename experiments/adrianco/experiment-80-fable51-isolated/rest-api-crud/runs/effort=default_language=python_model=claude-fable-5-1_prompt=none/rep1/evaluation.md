# Evaluation: effort=default_language=python_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=none, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective) — `defect_rate=1.0`, `test_coverage=0.92` from scores.json
- **Build:** pass — stdlib-only, no build step (import succeeds; tests ran)
- **Lint:** n/a — `code_quality=0.79` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:189-194` POST → `store.create`; 201 + Location header |
| R2 | GET /books lists all books | ✓ implemented | `app.py:186-188` → `BookStore.list` (`app.py:85-94`) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:187` parses `author`; `app.py:88-90` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:200-204`; 404 at `app.py:203` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:205-212`; `BookStore.update` returns None→404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:213-216`; 204 on success, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore` uses `sqlite3.connect` (`app.py:57`), real table (`app.py:60-70`) |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `_send_json`/`_error` (`app.py:128-143`); 200/201/204/400/404/405/413 |
| R9 | Validation: title and author required | ✓ implemented | `validate_book` (`app.py:30-35`); 400 at `app.py:173` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:180-183` returns `{"status":"ok"}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — run, endpoints, examples, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 12 funcs → 19 collected items; `test_coverage=0.92` |

No prompt-factor requirements (prompt=none).

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill §2):

```text
test_coverage = 0.92   # tests executed and passed; 0.92 line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.78
```

```text
pytest collect-only: 19 test items, 0 skips
grep skip/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py) | 269 |
| Lines of code (tests, test_app.py) | 159 |
| Files (excl. __pycache__/.coverage) | app.py, test_app.py, README.md, requirements-dev.txt (+ stack/task/meta) |
| Dependencies | 1 dev-only (pytest); 0 runtime (stdlib) |
| Tests total (collected) | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (no build step) |

## Findings

Full list in `findings.jsonl`:

1. [low] Single shared SQLite connection under a global lock serializes requests — `app.py:56-57`
2. [info] Line coverage 0.92 (not 1.0) — some error paths (413 / bad Content-Length) untested

No requirement, build, test, or skip findings — the run fully implements the spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=python_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json                                  # stored mechanical scores
grep -rE "pytest\.skip|xfail" test_app.py | wc -l  # 0 skips
python3 -m pytest --collect-only -q test_app.py  # 19 items
```
