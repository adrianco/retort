# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s1 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask, prompt=none, stack=s1
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — test_coverage=0.96 from scores.json
- **Build:** pass — not re-run (test_coverage=0.96 ⇒ import/build + tests succeeded)
- **Lint:** pass — code_quality=0.79, idiomatic=0.72 from scores.json
- **Architecture:** single-module Flask app (`app.py`) + pytest suite (`test_app.py`); summary skill not available in session
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `app.py:48 create_book`, persists via INSERT (app.py:72) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:83 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:86-92` WHERE author LIKE (substring) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:99 get_book`, 404 at app.py:104 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:108 update_book`, 404 at app.py:113 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:146 delete_book`, 404 at app.py:151 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,24-36` sqlite3 + CREATE TABLE books |
| R8 | JSON responses w/ appropriate status codes | ✓ implemented | jsonify + 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:57-60` (POST), `app.py:122-125` (PUT) |
| R10 | GET /health endpoint | ✓ implemented | `app.py:43-45` returns {"status":"healthy"},200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, run, curl examples, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 15 tests, test_coverage=0.96 |

## Build & Test

Scores read from `scores.json` (not re-run per skill policy):

```text
test_coverage = 0.96   # build/import + all tests passed, 96% coverage
defect_rate   = 1.0    # build+test succeeded
maintainability = 1.0
code_quality  = 0.7888
idiomatic     = 0.72
token_efficiency = 0.0192
```

Agent stdout reports "15/15 passed"; skip grep found 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 383 (app.py 160, test_app.py 223) |
| Files | 12 (incl. archive artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational:

1. [info] R3 `?author=` filter is substring (LIKE %x%), not exact match — acceptable per spec
2. [info] R5 PUT requires both title and author (full replace, no partial update)
3. [info] code_quality 0.79 / idiomatic 0.72 — minor quality/idiom gaps, no functional impact
4. [info] Low token_efficiency (0.019) — local-model verbosity metric, not a code defect

No requirement gaps, no skipped/disabled tests, no build/test failures.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s1/rep2"
cat scores.json                        # stored mechanical scores (build/test/lint)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l  # 0
grep -rcE "def test_" test_app.py      # 15
# To re-run tests independently: pip install -r requirements.txt && pytest test_app.py -v
```
