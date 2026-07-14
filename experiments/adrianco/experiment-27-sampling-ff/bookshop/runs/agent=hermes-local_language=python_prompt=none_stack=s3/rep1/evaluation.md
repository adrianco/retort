# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s3 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask, prompt=none, stack=s3
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `test_coverage=0.95` in scores.json (build + tests ran)
- **Lint:** pass — `code_quality=0.79` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Scores read from `scores.json` (inline gate, run not yet in retort.db):
`test_coverage=0.95`, `code_quality=0.789`, `defect_rate=1.0`, `maintainability=1.0`,
`idiomatic=0.6`, `token_efficiency=0.018`. Per skill policy the toolchain was **not**
re-run. Agent stdout reports "16/16 passed in 0.06s".

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:53-95` `create_book`; `test_create_book_success` |
| R2 | GET /books lists all | ✓ implemented | `app.py:98-112` `list_books`; `test_list_books_with_data` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:104-108` LIKE filter; `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:115-124`; `test_get_book_success`/`_not_found` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:127-172`; `test_update_book_success` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:175-187`; `test_delete_book_success` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:26-39` `init_db`; on-disk `books.db` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/409 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:67-70`; `test_create_book_missing_title`/`_author` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:47-50`; `test_health_check_returns_200` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, API docs, curl) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 16 tests; `test_coverage=0.95 > 0` |

## Build & Test

Not re-run — stored scores used per skill policy.

```text
scores.json: test_coverage=0.95  defect_rate=1.0  code_quality=0.789
_agent_stdout.log: "Test results: 16/16 passed in 0.06s"
grep "def test_" test_app.py = 16 ; skips (pytest.skip/xfail) = 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 194 |
| Lines of code (test_app.py) | 237 |
| Files (excl. caches) | 14 (incl. archive artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium findings.

1. [low] SEC1 — Flask run with `debug=True`, host `0.0.0.0` (`app.py:194`)
2. [low] BUG1 — `year` of 0 silently stored as NULL (`app.py:86,164`)
3. [info] OBS1 — `?author=` is a substring LIKE match, not exact (`app.py:106`)
4. [info] OBS2 — generated `books.db` committed into the workspace

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s3/rep1
cat scores.json
grep -cE "def test_" test_app.py
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
# to actually re-run (not required): pip install -r requirements.txt && pytest test_app.py -v
```
