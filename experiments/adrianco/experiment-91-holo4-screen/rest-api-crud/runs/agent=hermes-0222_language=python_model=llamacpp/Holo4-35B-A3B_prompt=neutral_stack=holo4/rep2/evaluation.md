# Evaluation: agent=hermes-0222 language=python model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0222, model=llamacpp/Holo4-35B-A3B, prompt=neutral, stack=holo4, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 entries)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.95, defect_rate=0.9242; tests executed)
- **Lint:** pass — code_quality=0.7722 from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist from the pinned `rest-api-crud/REQUIREMENTS.json` (constant denominator across runs). The prompt factor `neutral` prescribes no methodology and adds no checkable requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:59-91` create_book inserts all four fields; `test_app.py:32` test_create_book |
| R2 | GET /books lists all books | ✓ implemented | `app.py:94-106` list_books; `test_app.py:74` test_list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:100-101` WHERE author=?; `test_app.py:89` test_list_books_filter_by_author |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:109-116`; `test_app.py:104` + `test_app.py:117` not-found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:119-149`; `test_app.py:122` test_update_book |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:152-162` (204); `test_app.py:139` test_delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,7,26-39` sqlite3 + books.db, CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py` jsonify with 201/200/404/400/204 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:69-72` reject empty title/author (400); `test_app.py:52,63` |
| R10 | GET /health health check | ✓ implemented | `app.py:53-56` returns {"status":"ok"},200; `test_app.py:25` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:51-69` setup + run + tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` has 10 tests; test_coverage=0.95 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill policy):

```text
test_coverage   = 0.95    # tests executed and passed (coverage proportion)
defect_rate     = 0.9242  # build+test succeeded
code_quality    = 0.7722
maintainability = 1.0
idiomatic       = 0.55
token_efficiency= 0.0142
```

Agent self-report (`_agent_stdout.log`): "Ran focused test suite — all 10 tests pass".

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 324 (app.py 169 + test_app.py 155) |
| Files | app.py, test_app.py, README.md |
| Dependencies | Flask (documented in README; no requirements.txt) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| API calls / tokens | 19 calls, 367,125 tokens (cache_read 341,976) |

## Findings

Top findings (full list in `findings.jsonl`) — none at medium or above:

1. [low] No requirements.txt / pinned dependency file — Flask only via `pip install flask` in README
2. [info] `init_db()` runs as an import side effect (`app.py:166`)
3. [info] PUT with empty JSON body `{}` returns misleading "must be JSON" error (`app.py:122-124`)

This is a clean, fully-conformant run: every pinned requirement is implemented and exercised by a passing test, with correct REST status codes, SQLite persistence, input validation, and a documented README. Remaining findings are minor hygiene/edge-case notes, not spec gaps.

## Reproduce

```bash
cd "experiments/adrianco/experiment-91-holo4-screen/rest-api-crud/runs/agent=hermes-0222_language=python_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep2"
cat scores.json                       # stored build/test/quality scores (not re-run)
grep -cE "def test_" test_app.py      # 10 tests
grep -rE "skip|xfail" test_app.py     # 0 skips
# requirements checklist: ../../../../REQUIREMENTS.json (pinned, 12 entries)
```
