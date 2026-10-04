# Evaluation: rest-api-crud · effort=medium language=python model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=medium (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 18 test functions (many parametrized → ~33 effective cases) / 0 failed / 0 skipped
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.7888` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (scores.json, not re-run per skill step 2): test_coverage=0.94,
defect_rate=1.0, maintainability=1.0, idiomatic=0.83, code_quality=0.789,
token_efficiency=0.0499. defect_rate=1.0 ⇒ build + tests succeeded; 0.94 is line
coverage, not a test failure.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:202-206` → `BookStore.create` `app.py:58-64`; `test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:198-201` → `BookStore.list` `app.py:66-74`; `test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:199-201` + `WHERE author=? COLLATE NOCASE` `app.py:69-71`; `test_list_books_filtered_by_author` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.py:213-224` (404 at 222-223); `test_get_book`, `test_get_missing_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:215-216` → `BookStore.update` `app.py:80-88`; `test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:217-221` → `BookStore.delete` `app.py:90-93`; `test_delete_book` |
| R7 | Data in SQLite | ✓ implemented | `sqlite3.connect` `app.py:35`, schema `app.py:38-48`; `test_books_persist_across_store_instances` |
| R8 | JSON responses + status codes | ✓ implemented | `_send_json` `app.py:254-262`; 201/200/204/400/404/405/413/500 across `_route` |
| R9 | Validation: title & author required | ✓ implemented | `validate_book` `app.py:114-123`; `test_create_book_validation` |
| R10 | GET /health | ✓ implemented | `app.py:190-194` (pings DB); `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` (110 lines: Setup, Run, Test, API sections) |
| R12 | ≥3 tests | ✓ implemented | 18 test funcs in `test_app.py`; test_coverage=0.94>0 |

No prompt-factor requirements: `prompt=neutral` maps to the neutral instruction,
adds no checkable `P*` items beyond TASK.md.

## Build & Test

Not re-run (skill step 2 — scores present in `scores.json`).

```text
defect_rate  = 1.0    # build + tests succeeded
test_coverage= 0.94   # line coverage; all tests passed
code_quality = 0.789  # lint/quality
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 301 |
| Lines of code (test_app.py) | 229 |
| README lines | 110 |
| Files (source) | app.py, test_app.py, README.md, requirements-dev.txt |
| Dependencies (runtime) | 0 (stdlib only) |
| Dependencies (dev) | 1 (pytest) |
| Tests (functions) | 18 |
| Tests skipped | 0 |
| Skip ratio | 0% |
| Line coverage | 94% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Line coverage 94%, not full — 500 handler / some validation branches uncovered
2. [info] Stdlib-only implementation, no framework dependency
3. [info] Robustness beyond spec: body-size cap, 405 handling, Location header, persistence test

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=medium_language=python_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                    # stored build/test/lint scores (not re-run)
python -m pytest test_app.py -q    # optional: re-run tests (needs pytest)
grep -cE "^def test_" test_app.py  # test count
```
