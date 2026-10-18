# Evaluation: effort=low_language=python_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass (defect_rate=1.0 from scores.json) — tests execute without build step (stdlib only)
- **Lint:** n/a — code_quality=0.67 from scores.json (quality scorer, not a linter run)
- **Architecture:** stdlib-only layered design (app = HTTP/routing, db = SQLite store, validation = payload checks); `run-summary` skill unavailable, not invoked
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/app.py` `_create` → `bookapi/db.py` `create`; tested `test_create_then_get` |
| R2 | GET /books lists all books | ✓ implemented | `app.py` `_list` → `db.py` `list`; tested `test_list_filters_by_author_case_insensitively` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py` `_list` parses `author`; `db.py` `WHERE author = ? COLLATE NOCASE`; tested |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py` `_get` returns 404 on None; tested `test_delete_then_get_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py` `_update` → `db.py` `update`; tested `test_update_replaces_fields` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py` `_delete` → `db.py` `delete`; tested `test_delete_then_get_returns_404` |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/db.py` uses `sqlite3`, persistent file via `--db`/`BOOKS_DB_PATH` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/400/404/405/409 across `app.py`; JSON encoded in `_Handler._respond` |
| R9 | Input validation: title and author required | ✓ implemented | `bookapi/validation.py` `validate_book`; tested `test_create_rejects_missing_title_and_author` |
| R10 | GET /health endpoint | ✓ implemented | `app.py` `handle` returns `{"status":"ok"}`; tested `test_health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, run, test, endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 14 tests in `tests/test_api.py` (0 skipped) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 0.92   (coverage fraction; tests executed and passed)
defect_rate     = 1.0    (build + tests succeeded)
code_quality    = 0.6667
maintainability = 0.9176
idiomatic       = 0.85
token_efficiency= 0.0393
```

```text
grep 'def test_' tests/  ->  14 tests
grep skip/xfail          ->  0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 494 |
| Files (excl. caches) | 17 |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (stdlib, no build) |

## Findings

No correctness findings. 3 info-level notes (full list in `findings.jsonl`):

1. [info] Duplicate ISBN returns 409 Conflict (beyond spec)
2. [info] ISBN-10/ISBN-13 checksum validation (beyond spec)
3. [info] PUT performs a full replace (acceptable PUT semantics)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json
grep -rhE "^\s*def test_" tests/ | wc -l
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ | wc -l
```
