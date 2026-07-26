# Evaluation: hermes-local · python · mlxlocal/Qwen3-Coder-Next-4bit · prompt=neutral · stack=m80 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, task `rest-api-crud`)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — imports cleanly (test_coverage=0.94, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Clean run. A single Flask module (`app.py`) implements the full CRUD + health API
over SQLite; `test_app.py` covers every endpoint plus validation and not-found paths.
Stored scores confirm the suite builds and passes (test_coverage=0.94, defect_rate=1.0).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:97 create_book` inserts all four fields → 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:68 list_books`, `SELECT * FROM books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:74-79` `WHERE author = ?`; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:144 get_book`; 404 at `app.py:153-154` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:169 update_book`; 404 if missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:222 delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:29 sqlite3.connect`, `books` table schema |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:46-59 validate_book_data`; tests for missing title/author → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:62 health_check` → `{"status":"healthy"}`, 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — install, run, test, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 15 tests in `test_app.py`; test_coverage=0.94 |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json (computed during retort run)
test_coverage = 0.94   → build + all tests passed (94% line coverage)
defect_rate   = 1.0    → build + test succeeded
code_quality  = 0.789
maintainability = 0.979
idiomatic     = 0.63
token_efficiency = 0.029
```

```text
skip scan: grep -rE "pytest.skip|@pytest.mark.skip|xfail" → 0 matches
test functions: 15 (grep -cE "^def test_" test_app.py)
agent stdout self-report: "All 15 tests pass"
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 242 |
| Lines of code (test_app.py) | 264 |
| Files (excl. __pycache__/.git) | 14 (incl. run artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Coverage | 94% |
| API calls (hermes) | 13 |
| Tokens (in/out) | 33,558 / 5,691 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] `datetime.utcnow()` is deprecated (Python 3.12+) — `app.py:113,191`
2. [info] PUT is a full replacement (title+author required), not a partial update — conformant, spec doesn't require PATCH — `app.py:187`
3. [info] Test DB isolation relies on monkeypatching module-level `DATABASE` — `test_app.py:46-47`

No critical, high, or medium findings. No missing or partial requirements.

## Reproduce

```bash
cd "runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3"
cat scores.json                                   # stored build/test/quality scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # skip count → 0
grep -cE "^def test_" test_app.py                 # test count → 15
# Optional live run:
pip install flask pytest && python -m pytest test_app.py -v
```
