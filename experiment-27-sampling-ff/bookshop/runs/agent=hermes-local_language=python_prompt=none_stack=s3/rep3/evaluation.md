# Evaluation: agent=hermes-local language=python prompt=none stack=s3 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, prompt=none, stack=s3, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — per `_agent_stdout.log` (16/16 passed in 0.06s)
- **Build:** pass — from `scores.json` (`test_coverage=0.98`, `defect_rate=1.0`; not re-run)
- **Lint:** pass — from `scores.json` (`code_quality=0.79`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:50` `create_book`; `test_app.py:52` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:93` `list_books`; `test_app.py:105` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:99-102` LIKE filter; `test_app.py:117` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:110` `get_book`; `test_app.py:133,138` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:122` `update_book`; `test_app.py:154` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:158` `delete_book`; `test_app.py:189` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13,28` `sqlite3`; `books.db` present |
| R8 | JSON responses + appropriate HTTP codes | ✓ implemented | `jsonify` + 201/200/404/400 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:61-65`; `test_app.py:69,77` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:44` `health_check`; `test_app.py:37` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` Setup/Testing sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 16 tests in `test_app.py`; `test_coverage=0.98` |

## Build & Test

Not re-run — stored scores read from `scores.json` (per skill Step 2):

```text
scores.json: test_coverage=0.98  defect_rate=1.0  code_quality=0.789  maintainability=1.0  idiomatic=0.8
_agent_stdout.log: 16/16 tests passed in 0.06s
```

`test_coverage=0.98` ⇒ build succeeded and tests executed and passed; `defect_rate=1.0`
⇒ build+test succeeded. No skipped/xfail tests found (grep for skip markers = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 383 (app.py 177 + test_app.py 206) |
| Files (source, excl. artifacts) | 4 (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [low] README PUT example omits `author`, but `update_book` requires it (`app.py:139` → 400) — documented example would fail.
2. [info] `GET /books ?author=` is a substring `LIKE` match, not exact (`app.py:101`) — acceptable per spec.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s3/rep3
cat scores.json                                    # stored mechanical scores (no re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
# To re-verify manually (optional): pip install -r requirements.txt && pytest test_app.py -v
```
