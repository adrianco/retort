# Evaluation: rest-api-crud · effort=max language=python model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=max, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** passed (34 test functions, many parametrized) / 0 failed / 0 skipped — `test_coverage=0.99` from `scores.json`
- **Build:** pass — no build step (interpreted); modules import and tests run per `test_coverage=0.99`
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores (`scores.json`): test_coverage=0.99, code_quality=1.0, defect_rate=1.0, maintainability=0.982, idiomatic=0.82, token_efficiency=0.0037.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:51 create_book` → `database.py:47 insert_book`; `tests/test_books_api.py:62` |
| R2 | GET /books lists all | ✓ implemented | `app.py:57 list_books` → `database.py:64`; `tests/test_books_api.py:153` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:59` + `database.py:67-72` substring/casefold; `tests/test_books_api.py:170` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:63 get_book` raises NotFound; `tests/test_books_api.py:219,231` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:71 update_book` → `database.py:76`; `tests/test_books_api.py:242` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:80 delete_book` → `database.py:86`; `tests/test_books_api.py:293` |
| R7 | SQLite / embedded DB | ✓ implemented | `database.py:8 SCHEMA`, `connect()`; persists across instances `tests/test_books_api.py:348` |
| R8 | JSON responses + status codes | ✓ implemented | jsonify everywhere; 201/200/204/400/404/405/500; `app.py:87-103` |
| R9 | title & author required | ✓ implemented | `validation.py:22 parse_book`, `_required_text`; `tests/test_books_api.py:104` |
| R10 | GET /health | ✓ implemented | `app.py:42 health` (200 / 503); `tests/test_books_api.py:40,47` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, API table, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 34 test functions across 2 files; `test_coverage=0.99` |

## Build & Test

No compile step (Python). Per the skill, build/test/lint scores were read from `scores.json` rather than re-run:

```text
test_coverage = 0.99   # tests ran and passed (test gate)
code_quality  = 1.0    # lint/quality
defect_rate   = 1.0    # build+test succeeded
```

Note: a local `pytest --collect-only` errored on `tests/test_books_api.py` only because Flask is not installed in this evaluation environment (`import flask` fails here); this is environmental and not a defect in the run — the scorer's environment had Flask and recorded `test_coverage=0.99`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-blank) | 227 (app 88, database 67, validation 72) |
| Test code (non-blank) | 255 (api 229, validation 26) |
| Files (excl. artifacts) | 11 source/config + summary |
| Dependencies | Flask (runtime), pytest (dev) |
| Tests total (functions) | 34 (several parametrized → more cases) |
| Tests effective | 34+ (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (interpreted) |

## Findings

No correctness, build, or test defects. Three info-level enhancements (beyond spec):

1. [info] Accent-aware case-insensitive author filter (custom SQLite `casefold()`).
2. [info] JSON error handlers for 400/404/405/500 plus overflow-safe id route converter.
3. [info] ISBN-10/13 format validation and bounded year validation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                      # stored mechanical scores (no re-run)
grep -rE "pytest\.skip|xfail" tests/ # 0 skips
pip install -r requirements-dev.txt && pytest   # to re-verify (needs Flask)
```
