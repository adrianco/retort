# Evaluation: mlx-community/Qwen3-Coder-Next-4bit · prompt=neutral · stack=m80 · rep 2

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, prompt=neutral, stack=m80
- **Status:** ok — clean pass, all requirements implemented and tested
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, rest-api-crud)
- **Tests:** 22 passed / 0 failed / 0 skipped (22 effective) — per `_agent_stdout.log` "All 22 tests pass"
- **Build:** pass — `test_coverage=0.97`, `defect_rate=1.0` from `scores.json` (tests build+import and ran)
- **Lint:** pass — `code_quality=0.789`, `maintainability=0.970`, `idiomatic=0.78` from `scores.json`; no blocking warnings
- **Architecture:** single-module Flask app (`app.py`) + SQLite; `run-summary` skill not available in this session
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:117 create_book` inserts all four fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:88 get_books` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:94-99` filters by `author` query param; `test_app.py:202` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `app.py:164 get_book`, 404 at `app.py:174`; `test_app.py:102,124` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:189 update_book`, partial update at `app.py:222-225`; `test_app.py:130,242` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:249 delete_book`; `test_app.py:172` |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3` connection + `books` table, `app.py:29-45` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify(...), 200/201/400/404/500` throughout `app.py` |
| R9 | Input validation: title and author required | ✓ implemented | `validate_book_data` `app.py:48-72`; `test_app.py:70,86` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:75 health_check`; `test_app.py:32` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` install/usage/testing sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 22 tests in `test_app.py`, `test_coverage=0.97` |

Prompt factor `neutral` prescribes no methodology and asks for tests demonstrating the requirements — satisfied by the 22-test suite (no additional checkable P-requirements).

## Build & Test

```text
# Not re-run — stored scores used per evaluate-run skill (scores.json)
test_coverage = 0.97   # tests built, imported, and ran; ~97% coverage
defect_rate   = 1.0    # build + test succeeded
```

```text
pytest test_app.py -v   (as reported in _agent_stdout.log)
22 tests — all 22 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 272 |
| Lines of code (test_app.py) | 408 |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 2 (flask, pytest — README prose, unpinned) |
| Tests total | 22 |
| Tests effective | 22 |
| Skip ratio | 0% |
| code_quality | 0.789 |
| maintainability | 0.970 |
| token_efficiency | 0.026 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] `datetime.utcnow()` deprecated in Python 3.12+ — `app.py:83,129,219`
2. [low] `init_db()` runs as an import side effect on a CWD-relative path — `app.py:268`
3. [info] No `requirements.txt`/`pyproject.toml` pinning dependencies
4. [info] Whitespace-only title/author rejected on create+update (enhancement beyond spec)

No critical/high/medium findings — this is a clean conformance pass.

## Reproduce

```bash
cd "runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep2"
cat scores.json            # stored mechanical scores (test_coverage, defect_rate, ...)
grep -cE "^def test_" test_app.py                 # 22
grep -rE "pytest\.skip|xfail" test_app.py | wc -l # 0
```
