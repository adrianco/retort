# Evaluation: agent=qwen3-coder-local_language=python_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, prompt=neutral, framework=unknown (Flask, inferred)
- **Status:** ok — all requirements implemented; tests exist and ran
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 unittest tests present (0 skipped, 12 effective); coverage measured against `simple_test.py` only
- **Build:** pass — defect_rate=1.0 from `scores.json` (build+test succeeded)
- **Lint:** pass (no linter score; code_quality=0.833 from `scores.json`) — 1 duplicated-code issue
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low, 2 info)

Scores from `scores.json`: code_quality=0.833, test_coverage=0.19, defect_rate=1.0,
maintainability=0.835, idiomatic=0.68, token_efficiency=0.0064.

## Requirements

Checklist is the pinned `bookshop-256k/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:52-86` create_book; test `tests.py:test_create_book` |
| R2 | GET /books lists books | ✓ implemented | `app.py:89-109`; test `tests.py:test_get_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:94-97` LIKE filter; test `test_get_books_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:112-128`, 404 at :119-120; test `test_get_book_by_id` / `test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:131-173`; test `test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:176-191`; test `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18-31` sqlite3 + `books.db` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` with 201/200/404/400/500 throughout `app.py` |
| R9 | Validation: title+author required | ✓ implemented | `app.py:57` (and :146 for PUT); test `test_create_book_missing_fields` |
| R10 | GET /health | ✓ implemented | `app.py:47-49`; test `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md:29-88` (minor: no `pip install`, see findings) |
| R12 | ≥3 tests that run | ✓ implemented | `tests.py` 12 tests; test_coverage=0.19 (>0) |

No `P*` prompt requirements: the `neutral` prompt prescribes no methodology and only
asks for tests demonstrating the implementation — already covered by R12.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; no `retort.db` row yet).

```text
scores.json: defect_rate=1.0  → build + tests succeeded
             test_coverage=0.19 → coverage measured on simple_test.py (.coverage), not tests.py
             code_quality=0.833, maintainability=0.835, idiomatic=0.68
```

```text
tests.py — 12 unittest methods (health, CRUD, validation, 404s, unique-ISBN); 0 skips
simple_test.py — 1 live-server smoke function (spawns app.py on :5001 via requests)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 489 (app.py 197, tests.py 197, simple_test.py 95) |
| Files (source/docs, excl. logs/db) | 7 |
| Dependencies | Flask (+ requests for simple_test.py); no manifest file |
| Tests total | 13 (12 unittest + 1 smoke) |
| Tests effective | 12 (unittest suite; 0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Duplicated imports, DATABASE constant, and Flask app in `app.py:1-15`
2. [medium] `simple_test.py` is a live-server integration script collected as a test (drove coverage=0.19)
3. [low] No dependency manifest / no `pip install flask` step in README
4. [info] `?author=` filter uses LIKE substring match rather than exact match
5. [info] Reported test_coverage 0.19 reflects `simple_test.py`, not the real `tests.py` suite

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=python_prompt=neutral/rep1
cat scores.json                       # mechanical scores (build/test/lint)
sqlite3 -readonly .coverage "SELECT f.path FROM file f;"   # coverage target = simple_test.py
grep -cE 'def test_' tests.py         # 12
grep -rEn 'skip|xfail' *.py           # 0 skips
```
