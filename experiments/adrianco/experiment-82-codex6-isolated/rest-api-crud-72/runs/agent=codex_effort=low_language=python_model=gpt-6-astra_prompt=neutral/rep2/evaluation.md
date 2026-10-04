# Evaluation: agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-6-astra, effort=low, prompt=neutral, framework=unknown (Flask)
- **Status:** ok (self-repair run — previous attempt's build/tests failed; this one fixes the existing code)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=0.98 from scores.json (build + tests executed)
- **Lint:** pass with warnings — ~10 lines over 88 chars (ruff E501); code_quality=0.62
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:72` `create_book`, INSERT at `app.py:76`, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `app.py:81` `list_books`, SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:87` `WHERE author = ?`; test `test_author_filter` |
| R4 | GET /books/{id} by id (404 if absent) | ✓ implemented | `app.py:91` `get_book`, `get_book_or_404` raises NotFound `app.py:64` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:95` `update_book`, UPDATE at `app.py:101` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:107` `delete_book`, DELETE + 404 on no rows |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15` `sqlite3.connect`, CREATE TABLE `app.py:27` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/415 via HTTPException handler `app.py:35` |
| R9 | Input validation: title & author required | ✓ implemented | `validate_book` `app.py:49-51` raises 400; `test_required_fields_on_create_and_update` |
| R10 | GET /health | ✓ implemented | `app.py:67` `health`, pings DB, returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, API table, tests |
| R12 | >= 3 unit/integration tests | ✓ implemented | `test_app.py` 8 test methods, test_coverage=0.98 |

No requirement is a stub; each route is exercised by at least one test.

## Build & Test

Build/test not re-run — stored scores used per skill policy.

```text
scores.json (from retort scoring):
  test_coverage   = 0.98   (build + tests executed; coverage fraction)
  defect_rate     = 0.07   (low: driven by ruff E501 long-line count / LOC)
  maintainability = 1.00
  idiomatic       = 0.87
  code_quality    = 0.62   (E501 style warnings)
  token_efficiency= 0.04
```

```text
tests: 8 unittest methods, 0 skipped (grep for skip/xfail markers → 0)
  test_crud, test_author_filter, test_validation,
  test_json_errors_and_missing_books, test_health_and_persistence,
  test_update_all_fields_and_persist_deletion,
  test_required_fields_on_create_and_update,
  test_optional_fields_and_string_normalization
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py + test_app.py) | 246 |
| Files (top level) | 15 (2 source) |
| Dependencies | 1 (Flask) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] 10 source lines exceed the 88-char limit (ruff E501) — stylistic only
2. [info] GET /books?author= filter is exact and case-sensitive — documented, spec-compliant

## Reproduce

```bash
cd experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep2
cat scores.json
grep -cE "def test" test_app.py
python -m unittest discover -v   # optional; scores already recorded
```
