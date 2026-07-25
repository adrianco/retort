# Evaluation: gptoss-20b · python · neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from scores.json (defect_rate=1.0)
- **Lint:** pass — code_quality=0.79 (unused import, Pydantic v1 idioms)
- **Architecture:** run-summary skill unavailable in this environment — see app.py (single-module FastAPI + SQLAlchemy service)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 3 low)

Scores read from `scores.json` (inline gate; no re-run): test_coverage=0.94, defect_rate=1.0, code_quality=0.789, maintainability=0.593, idiomatic=0.73, token_efficiency=0.003.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:102` create_book, persists via SQLAlchemy |
| R2 | GET /books lists all | ✓ implemented | `app.py:116` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:122-123` `where(Book.author == author)`; test `test_list_filter_author` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:129` get_book, 404 if absent |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:138` update_book |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:152` delete_book, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:20-49` SQLAlchemy + SQLite engine (see db-1 finding re: mis-named file) |
| R8 | JSON + HTTP status codes | ✓ implemented | 201 create, 200 get/list, 404 missing, 204 delete |
| R9 | title/author required | ✓ implemented | `app.py:56-57` Field(min_length=1) (returns 422, see r9-1) |
| R10 | GET /health | ✓ implemented | `app.py:96` health -> {"status":"ok"}; `test_health` |
| R11 | README setup/run | ✓ implemented | `README.md` setup + uvicorn run + test instructions |
| R12 | >= 3 tests | ✓ implemented | `tests/test_app.py` — 5 tests, all pass |

## Build & Test

Scores taken from `scores.json` (skill step 2 — do not re-run):

```text
test_coverage = 0.94   # tests executed and passed
defect_rate   = 1.0    # build + test succeeded
0 skips (grep pytest.skip/xfail over tests/ -> 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 131 |
| Files (source) | 3 (app.py, tests/test_app.py, README.md) |
| Dependencies | 6 (requirements.txt) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| API calls (agent) | 40 |
| Total tokens | 1,079,812 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Default DATABASE_URL is a malformed in-memory URI that creates a mis-named on-disk file `file::memory:` — `app.py:28`
2. [medium] Test reset fixture is a no-op (deletes non-existent `books.db`), so tests share DB state — `tests/test_app.py:12`
3. [low] Missing-field validation returns 422, not the 400 named in the checklist — `app.py:56-57`
4. [low] 204 No Content response carries a JSON body — `app.py:159`
5. [low] Unused `validator` import and Pydantic v1 `orm_mode` idiom — `app.py:19,77`

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep1
cat scores.json                                  # stored mechanical scores (no re-run)
grep -rE "pytest\.skip|xfail" tests/ | wc -l     # 0 skips
grep -cE "^def test_" tests/test_app.py          # 5 tests
```
