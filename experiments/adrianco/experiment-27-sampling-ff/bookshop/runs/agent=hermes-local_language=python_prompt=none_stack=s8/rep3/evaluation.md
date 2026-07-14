# Evaluation: agent=hermes-local language=python prompt=none stack=s8 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (model `Qwen3.6-35B-A3B`), prompt=none, stack=s8, framework=flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 37 passed / 0 failed / 0 skipped (37 effective) — `test_coverage=0.96`, `defect_rate=1.0` from `scores.json`
- **Build:** pass — build+test gate succeeded (`defect_rate=1.0`); not re-run
- **Lint:** pass — `code_quality=0.789` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores read from `scores.json` (inline gate; not re-run): `test_coverage=0.96`,
`code_quality=0.7889`, `defect_rate=1.0`, `maintainability=1.0`,
`idiomatic=0.68`, `token_efficiency=0.0122`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:59` create_book; `test_app.py:77` test_create_book_success |
| R2 | GET /books lists all books | ✓ implemented | `app.py:98` list_books; `test_app.py:150` test_list_books_returns_all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:103-106` `WHERE author LIKE ?`; `test_app.py:165` test_list_books_filter_by_author |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:112` get_book; `test_app.py:186/205` success + not_found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:122` update_book; `test_app.py:218` test_update_book_success |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:165` delete_book; `test_app.py:274` test_delete_book_success |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17` sqlite3.connect; `app.py:28-41` init_db CREATE TABLE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify throughout; 201/200/404/400/409; `test_app.py:517` TestHTTPStatusCodes |
| R9 | Validation: title + author required | ✓ implemented | `app.py:71-75`; `test_app.py:97/110/389` missing/empty tests |
| R10 | GET /health health check | ✓ implemented | `app.py:55` health → `{status: healthy}` 200; `test_app.py:54` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — Setup, Run, endpoints, curl examples, validation rules |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 37 test functions; `test_coverage=0.96 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill Step 2).

```text
scores.json: test_coverage=0.96, defect_rate=1.0
=> build + import + test gate PASSED
```

```text
grep -cE "def test_" test_app.py  => 37
grep skip/xfail markers           => 0 skipped
agent stdout: "All 37 tests pass, zero failures."
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-blank) | 677 (app.py 140, test_app.py 537) |
| Files (non-git) | 14 (2 source, plus README, requirements.txt, artifacts: books.db, .coverage) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 37 |
| Tests effective | 37 |
| Skip ratio | 0% |
| Coverage | 96% (`test_coverage=0.96`) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Dead helper `make_test_client` — unused yield-based generator at `test_app.py:11`; all tests use `make_client()`.
2. [info] Enhancement: duplicate-ISBN 409 handling beyond spec (`app.py:37,95-96,162-163`).
3. [info] Enhancement: integer year validation beyond spec (`app.py:77-81`).

No critical/high/medium findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s8/rep3
cat scores.json                                  # mechanical scores (not re-run)
grep -cE "def test_" test_app.py                 # 37
grep -rEn "pytest\.skip|xfail" . --include="*.py" # 0 skips
# to actually run: pip install -r requirements.txt && pytest test_app.py -v
```
