# Evaluation: rest-api-crud · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=none, effort=default (agent/framework=unknown)
- **Task:** REPAIR task — prior attempt had failed; this run fixed it.
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all pass / 0 failed / 0 skipped (12 test functions, ~19 effective cases incl. an ×8 parametrize)
- **Build:** pass (test_coverage=0.97 from scores.json ⇒ build + tests ran and passed)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate output — no re-run): `test_coverage=0.97`, `defect_rate=1.0`, `maintainability=1.0`, `idiomatic=0.88`, `code_quality=0.7889`, `token_efficiency=0.0210`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:83 create_book` INSERTs title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:98 list_books` SELECT all, ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:99-104` WHERE author = ? COLLATE NOCASE; test `test_list_books_and_author_filter` |
| R4 | GET /books/{id} by id | ✓ implemented | `app.py:109 get_book`, 404 via `fetch_book`; `test_not_found_is_json` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:116 update_book` UPDATE, 404 if absent; `test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:133 delete_book`, 204/404 via rowcount; `test_delete_book` |
| R7 | Stored in SQLite | ✓ implemented | `app.py:16 SCHEMA`, sqlite3 connections; `test_data_persists_across_app_instances` |
| R8 | JSON + correct status codes | ✓ implemented | `app.py:182-186` JSON body + Content-Type; 201/200/204/400/404/405/409 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:27 validate_book` → 400; `test_create_validation_errors` (×8) |
| R10 | GET /health | ✓ implemented | `app.py:79 health` returns `{status: ok}`; `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Endpoints, Tests sections |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 12 test functions, test_coverage=0.97 |

## Build & Test

Not re-run — scores read from `scores.json` (inline eval gate):

```text
test_coverage = 0.97   (build + all tests ran and passed)
defect_rate   = 1.0    (build+test succeeded)
```

Skip detection: `grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py` → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 196 (app.py) + 176 (test_app.py) = 372 |
| Files (excl. .git/.coverage) | ~14 (incl. harness logs); source: app.py, test_app.py, README.md, requirements.txt |
| Dependencies | 1 (pytest, tests only) |
| Tests total | 12 functions (~19 effective cases) |
| Tests effective | ~19 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`) — all informational; no defects:

1. [info] Zero-dependency stdlib WSGI implementation (`app.py:14`, `requirements.txt`)
2. [info] Duplicate-ISBN 409 handling and 405 with Allow header beyond spec (`app.py:93`, `app.py:172-173`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=python_model=claude-fable-5-1_prompt=none/rep2"
cat scores.json                                    # stored mechanical scores (no re-run)
grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # skip count
# optional full re-run: python -m pytest
```
