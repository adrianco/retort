# Evaluation: agent=hermes-local language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown, prompt=neutral (model Qwen3.6-35B-A3B via local stack)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — from scores.json (test_coverage=0.95, defect_rate=1.0; tests import + run)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:46 create_book` persists Book with title/author/year/isbn |
| R2 | GET /books lists all | ✓ implemented | `app.py:80 list_books` returns `Book.query.all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:86-89` case-insensitive author filter; `test_filter_books_by_author` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:96 get_book`, 404 when absent; `test_get_book_not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:107 update_book`; `test_update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:144 delete_book`; `test_delete_book` |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:9` sqlite URI; `books.db` present, SQLAlchemy model |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:57-61` reject empty; `test_create_book_missing_title/author` (see R9-robustness finding for non-string edge) |
| R10 | GET /health | ✓ implemented | `app.py:40 health_check` returns `{status: healthy} 200`; `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, usage, API reference |
| R12 | ≥ 3 tests | ✓ implemented | 14 tests in `test_app.py`, test_coverage=0.95 |

**Prompt factor (neutral):** the neutral prompt prescribes no methodology and only asks to "include tests that demonstrate the implementation meets the requirements" — satisfied by the 14-test suite. No additional checkable P-requirements.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.95   # tests import + execute + pass (coverage fraction)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.73
```

```text
pytest test_app.py    # 14 tests, 0 skips (grep), all passing per test_coverage
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 365 (app.py 163 + test_app.py 202) |
| Files | 13 (incl. artifacts: books.db, .coverage) |
| Dependencies | 2 (flask, flask-sqlalchemy — README only, no requirements.txt) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] Non-string title/author yields 500 instead of 400 — `app.py:57,121,127` call `.strip()` on raw JSON value
2. [low] No requirements.txt / pyproject.toml — deps only in README pip line
3. [info] Year type validation beyond spec (enhancement) — `app.py:67-71`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
grep -rE "^def test_" test_app.py | wc -l         # 14 tests
# to actually run: pip install flask flask-sqlalchemy && pytest test_app.py -v
```
