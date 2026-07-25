# Evaluation: agent=hermes-local · language=python · model=mlxlocal/Qwen3-Coder-Next-4bit · stack=m80 · prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — from scores.json defect_rate=1.0 (build+test succeeded)
- **Lint:** pass — code_quality=0.7889 (from scores.json); 0 lint failures, one deprecation nit
- **Architecture:** single-module Flask app (`app.py`) + integration tests (`test_api.py`); run-summary skill not available in this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (rest-api-crud), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:57-91` INSERT of all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:94-111` returns `{books: [...]}` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:97,102-103` WHERE author=?; `test_api.py:157` filter test |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `app.py:114-126` 404 branch at :123 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:129-186` dynamic update, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:189-204` DELETE + 404 branch |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4,17,30-45` sqlite3 with persistent `books.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify(...)` throughout; 200/201/400/404 used |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:66-70` reject empty/missing; `test_api.py:75-127` |
| R10 | GET /health health check | ✓ implemented | `app.py:48-54` returns `{status: healthy}` 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:19-33` setup/run; `:81-91` tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_api.py` has 15 `test_` methods |

No enhancements beyond spec except test breadth (15 tests vs. 3 required).

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; not yet in retort.db):

```text
test_coverage = 0.95   (line coverage; tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
maintainability = 0.9892
idiomatic     = 0.68
```

Skip scan (`grep -rE "pytest.skip|@pytest.mark.skip|xfail|unittest.skip"`) → 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + test_api.py) | 494 |
| Files (source) | 4 (app.py, test_api.py, requirements.txt, README.md) |
| Dependencies | 1 (flask>=2.0.0) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] All 12 pinned requirements implemented with 15 passing tests — spec fully satisfied.
2. [low] `datetime.utcnow()` deprecated in Python 3.12+ (`app.py:53,74`).
3. [low] POST with wrong content-type hits Flask's 415 rather than the intended 400 path (`app.py:60-63`); `request.get_json(silent=True)` would route it to validation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3"
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail|unittest\.skip" . --include="*.py" | wc -l
grep -cE "def test_" test_api.py
# to actually run (optional; scores already stored):
#   pip install -r requirements.txt && python -m pytest test_api.py -v
```
