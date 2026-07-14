# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s5 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=Flask, prompt=none, stack=s5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.97, defect_rate=1.0; tests build + import cleanly)
- **Lint:** pass — code_quality=0.79 (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean run. Every pinned requirement is implemented and exercised by a test; build and tests pass with 97% coverage and no skips.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:59-93 create_book`; `test_app.py:48 test_create_book_success` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:96-111 list_books`; `test_app.py:119 test_list_books_with_data` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:101-107` (LIKE); `test_app.py:134 test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:114-123 get_book`; `test_app.py:156,168` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:126-164 update_book`; `test_app.py:177,199` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:167-179 delete_book`; `test_app.py:218,232` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13,28-38 init_db`; `books.db` present |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify(...), 201/200/404/400` throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:70-74`; `test_app.py:66,76` |
| R10 | GET /health health-check | ✓ implemented | `app.py:53-56 health_check`; `test_app.py:33,38` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` (install, run, test, curl examples) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 17 tests in `test_app.py`; test_coverage=0.97 |

No prompt factor (prompt=none), so no `P*` instructions.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2):

```text
scores.json
  test_coverage = 0.97   # build + all tests pass; 97% line coverage
  defect_rate   = 1.0    # build + test succeeded
  code_quality  = 0.7889
  maintainability = 1.0
  idiomatic     = 0.8
  token_efficiency = 0.029
```

Agent self-report (`_agent_stdout.log`): "Test results: 17/17 passed in 0.07s". Skip scan (`grep pytest.skip|xfail`): 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 423 (app.py 187 + test_app.py 236) |
| Files | 5 tracked (app.py, test_app.py, requirements.txt, README.md, + books.db artifact) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |
| Tokens (total) | 221,186 across 11 API calls (Qwen3.6-35B-A3B) |

## Findings

Full list in `findings.jsonl` (2 info, nothing at low or above):

1. [info] Author filter uses substring (LIKE) match rather than exact match — `app.py:104-107` (parameterized, no injection risk)
2. [info] test_coverage 0.97: only the `__main__` dev-server guard is uncovered — `app.py:185-186`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s5/rep1
cat scores.json                                  # mechanical scores (not re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
grep -cE "def test_" test_app.py                 # 17
# to actually run: python -m pytest test_app.py -v
```
