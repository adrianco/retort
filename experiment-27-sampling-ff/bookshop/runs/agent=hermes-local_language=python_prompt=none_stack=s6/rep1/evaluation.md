# Evaluation: agent=hermes-local language=python prompt=none stack=s6 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s6, framework=unknown (Flask, inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — test_coverage=0.95, defect_rate=1.0 from `scores.json`
- **Lint:** pass — code_quality=0.7889 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:88 create_book` INSERTs title/author/year/isbn; `test_app.py:46 test_create_book_success` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:110 list_books`; `test_app.py:124 test_list_books_with_data` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:117-120` LIKE filter; `test_app.py:139 test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:126 get_book` (404 if absent); `test_app.py:162/178` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:136 update_book`; `test_app.py:189 test_update_book_success` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:187 delete_book`; `test_app.py:234 test_delete_existing_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,27-40` sqlite3 `books` table, `books.db` file |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:54-73 validate_book_data`; `test_app.py:80/93 missing_title/author → 400` |
| R10 | GET /health | ✓ implemented | `app.py:82 health_check` returns `{status: healthy} 200`; `test_app.py:35` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, API usage, testing sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 17 tests in `test_app.py`; test_coverage=0.95 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.95   (build + tests executed; all pass)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.68
token_efficiency = 0.0200
```

Agent's own report (`_agent_stdout.log`): "17/17 passed in 0.08s".

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 201 (app.py) + 296 (test_app.py) = 497 |
| Files | 13 (incl. archive artifacts) — 4 source deliverables |
| Dependencies | 2 (flask, pytest) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] init_db() runs on every request via `before_request` (`app.py:76-79`) — extra connection + DDL per request.
2. [info] Year validation beyond spec (0–2100 range + integer check) (`app.py:66-72`).
3. [info] PUT supports partial updates, preserving unspecified fields (`app.py:168-171`).

No critical, high, or medium findings. All 12 pinned requirements are implemented with passing tests.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s6/rep1
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l   # skip count = 0
grep -rEc "def test_" test_app.py      # 17 tests
# (optional) re-run: pip install -r requirements.txt && pytest test_app.py -v
```
