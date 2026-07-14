# Evaluation: language=python · model=sonnet-4.6 · prompt=tdd · rep 1

## Summary

- **Factors:** language=python, model=sonnet-4.6, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — `test_coverage=0.97` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 4 info)

Scores read from `scores.json` (inline eval gate): `test_coverage=0.97`,
`code_quality=0.789`, `defect_rate=1.0`, `maintainability=1.0`, `idiomatic=0.58`,
`token_efficiency=0.011`. Toolchain was **not** re-run per skill guidance.

## Requirements

Denominator is the pinned `rest-api/REQUIREMENTS.json` (12 requirements, fixed for all runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:62 create_book`, `BookIn` (app.py:22-26); `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:75 list_books`; `test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:80-81`; `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:87 get_book`, 404 at :93; `test_get_book` + `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:99 update_book`, 404 at :105; `test_update_book` + not-found |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:115 delete_book` (204), 404 at :121; `test_delete_book` + not-found |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:7 sqlite:///./books.db`, SQLAlchemy `BookRecord`; `books.db` present |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204 + 404 via `HTTPException`; `response_model` serialization |
| R9 | Validation: title & author required | ✓ implemented | `BookIn` required + `field_validator` not_empty (app.py:28-33); `test_create_book_missing_*` → 422 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:57 health`; `test_health` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — install, uvicorn run, endpoints, test commands |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 12 tests, `test_coverage=0.97` |

Prompt factor `tdd` (process guidance, not verifiable from final state): the agent
log (`_agent_stdout.log`) documents six red→green cycles and the 12 tests map 1:1
to handlers incl. not-found paths — consistent with test-first development.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill step 2).

```text
scores.json: test_coverage=0.97  defect_rate=1.0  maintainability=1.0
             code_quality=0.789   idiomatic=0.58   token_efficiency=0.011
```

`test_coverage=0.97` and `defect_rate=1.0` ⇒ the build succeeded and all tests
passed. Agent log confirms: "All 12 tests pass." No skipped/xfail tests (grep: 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 125 (`app.py`) + 90 (`test_app.py`) = 215 |
| Files | 12 (incl. `books.db`, `.coverage`) |
| Dependencies | 4 (README: fastapi, sqlalchemy, httpx, pytest — no lockfile) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | not re-run (scores cached) |

## Findings

Full list in `findings.jsonl` (5 items, none ≥ high — this is a clean run):

1. [low] `get_db()` dependency defined but never used — handlers open their own sessions (`app.py:49-54`)
2. [info] Missing title/author returns 422, not 400 — idiomatic FastAPI, satisfies spec
3. [info] PUT full-replacement nulls omitted optional fields (`app.py:106-107`)
4. [info] Validation rejects whitespace-only title/author — enhancement beyond spec
5. [info] TDD adherence consistent with agent log + test structure

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=python_model=sonnet-4.6_prompt=tdd/rep1
cat scores.json                                   # cached mechanical scores (not re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0 skips
grep -cE "^def test_" test_app.py                 # 12 tests
# Optional re-run (skill says NOT to when scores exist):
# python -m pytest test_app.py -v
```
