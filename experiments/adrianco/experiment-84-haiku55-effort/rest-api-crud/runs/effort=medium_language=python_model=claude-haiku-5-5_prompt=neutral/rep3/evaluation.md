# Evaluation: effort=medium language=python model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** ~23 passed / 0 failed / 0 skipped (~23 effective) — 16 test functions, one parametrized over 8 cases
- **Build:** pass — from `test_coverage=0.99` (scores.json): build imported + tests executed
- **Lint:** pass — `code_quality=0.9556` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:137 create_book` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:152 list_books` returns ordered collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:154-160` case-insensitive author WHERE; `test_app.py:56` |
| R4 | GET /books/{id} single book by id | ✓ implemented | `app.py:167 get_book`, 404 via `not_found()` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:174 update_book`, 404 if absent; `test_app.py:85` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:187 delete_book` returns 204; `test_app.py:114` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:11-19` schema, `sqlite3` persistence; `test_app.py:169` cross-instance persist test |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/405 across handlers + error handlers `app.py:121-131` |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:43-51 validate_book`; `test_app.py:125` parametrized rejections |
| R10 | GET /health health check | ✓ implemented | `app.py:133 health` returns `{"status":"ok"}`; `test_app.py:26` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` setup/run/test/API sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 16 test functions, ~23 effective cases; `test_coverage=0.99` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 0.99   # build imported + tests executed and passed
code_quality    = 0.9556
defect_rate     = 1.0    # build+test succeeded
maintainability = 1.0
idiomatic       = 0.42
token_efficiency= 0.0150
```

No skipped/xfail tests: `grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 377 (app.py 200 + test_app.py 177) |
| Files | 12 (incl. .coverage, logs, caches) |
| Dependencies | 3 (Flask, pytest, Werkzeug) |
| Tests total | 16 functions (~23 cases) |
| Tests effective | ~23 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (scores read from DB/scores.json) |

## Findings

Full list in `findings.jsonl`:

1. [low] Schema-init `with sqlite3.connect(...)` never closes the connection — leaks one per `create_app()` (`app.py:90`)
2. [info] PUT is full-replace (omitted fields reset to NULL) — matches spec, noted only (`app.py:174`)

No critical/high/medium findings. All 12 pinned requirements implemented and exercised by tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=medium_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                     # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json      # pinned 12-item checklist
grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0 skips
# Optional re-run: pytest   (test_coverage=0.99 already confirms pass)
```
