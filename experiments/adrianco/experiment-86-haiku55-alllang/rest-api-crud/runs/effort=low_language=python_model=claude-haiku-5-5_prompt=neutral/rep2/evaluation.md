# Evaluation: rest-api-crud · effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 8 test functions (one parametrized ×6 → 13 effective cases) passed / 0 failed / 0 skipped
- **Build:** pass — from `test_coverage=0.95` in `scores.json` (tests executed ⇒ imports/build OK)
- **Lint:** pass — `code_quality=0.62` (mechanical, no blocking warnings)
- **Architecture:** single-module stdlib app — `app.py` (`Store` SQLite wrapper + `BaseHTTPRequestHandler` router) and `test_app.py` (black-box HTTP tests against a live server on port 0)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:256 _post_books` → `Store.create` (app.py:71) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:251 _get_books` → `Store.list` (app.py:81) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:252-254` reads `author` query → `Store.list(author=)`; case-insensitive (app.py:85), tested `test_app.py:76` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:260 _get_book`, 404 at app.py:263 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:266 _put_book` → `Store.update` (app.py:89), merges existing fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:273 _delete_book` → `Store.delete` (app.py:100), 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:9,35-48` sqlite3 with on-disk DB + schema |
| R8 | JSON responses, correct status codes | ✓ implemented | `app.py:169 _send` sets JSON content-type; 201/200/204/400/404/405/500 across dispatch |
| R9 | Validation: title & author required | ✓ implemented | `app.py:115 validate_book`; rejected cases tested `test_app.py:92` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:248 _get_health` → `{"status":"ok"}`, tested `test_app.py:38` |
| R11 | README.md setup & run instructions | ✓ implemented | `README.md` — Requirements/Setup/Run/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 8 functions, test_coverage=0.95 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage   = 0.95   (tests executed; build/import OK)
defect_rate     = 1.00   (build+test succeeded)
code_quality    = 0.62
maintainability = 0.91
idiomatic       = 0.82
token_efficiency= 0.024
```

No skipped/xfail tests (`grep` of `pytest.skip|@pytest.mark.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 305 (app.py) + 121 (test_app.py) = 426 |
| Files | 4 (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 8 functions / 13 effective cases |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

All findings are info-level (no requirement impact); full list in `findings.jsonl`:

1. [info] code_quality score 0.62 — cosmetic (long lines / branching in validation)
2. [info] Coverage 0.95 not 1.0 — uncovered lines are the `main()`/`serve_forever` CLI entrypoint, intentionally not unit-tested
3. [info] No UNIQUE constraint on isbn / no 409 — beyond spec, not required

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # cached mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
# optional re-run: python -m pytest test_app.py -q
```
