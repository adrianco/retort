# Evaluation: agent=hermes-local language=python model=gpt-oss-20b-MXFP4-Q8 prompt=neutral stack=gptoss · rep 1

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `test_coverage=0.94`, `defect_rate=1.0` (scores.json); tests import & run
- **Lint:** pass — `code_quality=0.7889` (scores.json); a few v2 deprecations / unused import
- **Architecture:** run-summary skill not invoked (single-module FastAPI app; see below)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:102` `create_book` persists BookCreate |
| R2 | GET /books lists all | ✓ implemented | `app.py:116` `list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:122` `.where(Book.author == author)` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.py:129` `get_book`, 404 at `:133` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:138` `update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:152` `delete_book`, 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:20-49` SQLAlchemy + SQLite engine (see db-url finding) |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/204 across routes; `response_model=BookOut` |
| R9 | Validation: title+author required | ✓ implemented | `app.py:56-57` `Field(..., min_length=1)` (rejects 422, not 400; untested — info finding) |
| R10 | GET /health | ✓ implemented | `app.py:96` `health` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup / Running / tests sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `tests/test_app.py` 5 tests, `test_coverage=0.94` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill Step 2):

```text
test_coverage = 0.94   # build + tests import and run; all pass
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.7889
maintainability = 0.5929
idiomatic     = 0.73
```

```text
pytest  (5 tests in tests/test_app.py)
test_health, test_create_and_get_book, test_list_filter_author,
test_update_book, test_delete_book — all passed (agent stdout: "All tests passed"); 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 131 |
| Lines of code (tests, non-blank) | 51 |
| Files (excl. session/coverage/stray-db) | ~12 |
| Dependencies (requirements.txt) | 6 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Full list in `findings.jsonl`:

1. [low] Default `DATABASE_URL` creates a stray on-disk file `file::memory:` instead of a true in-memory DB (`app.py:28`)
2. [low] Unused import `validator` (`app.py:19`)
3. [info] Pydantic v1 `orm_mode` deprecated under v2 (`app.py:77`)
4. [info] Validation rejects with 422 not 400; no negative-validation test (`app.py:56`, `tests/test_app.py`)

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep1
cat scores.json                     # cached mechanical scores
grep -rE "def test_" tests/ | wc -l # 5 tests
grep -rE "pytest\.skip|xfail" tests/ | wc -l  # 0 skips
```
