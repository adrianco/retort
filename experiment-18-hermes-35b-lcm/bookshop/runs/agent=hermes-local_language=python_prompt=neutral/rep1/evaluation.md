# Evaluation: agent=hermes-local language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (FastAPI in practice), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass — `test_coverage=1.0` (build + all tests ran; scores.json)
- **Lint:** pass — `code_quality=0.833` (scores.json); 0 warnings observed
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:91` create_book; `test_app.py:48` test_create_book_success |
| R2 | GET /books lists all books | ✓ implemented | `app.py:110` list_books; `test_app.py:94` test_list_books_all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:114-117`; `test_app.py:102` test_list_books_filter_by_author |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `app.py:125` get_book; `test_app.py:116,124` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:137` update_book (partial via exclude_unset); `test_app.py:132` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:173` delete_book (204); `test_app.py:151` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17-44` sqlite3 + init_db; `books.db` present |
| R8 | JSON responses with correct status codes | ✓ implemented | 201/200/404/204 across handlers; asserted throughout test_app.py |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:53-56` Field(min_length=1) → 422; `test_app.py:70-83` |
| R10 | GET /health health-check | ✓ implemented | `app.py:86` health_check; `test_app.py:30` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (Setup/Run/Testing sections) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 15 test functions in `tests/test_app.py`; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   → build + all tests executed and passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.833
maintainability = 0.9995
idiomatic     = 0.63
```

15 test functions, 0 skips (`grep pytest.skip/xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 349 (app.py 185, tests 164) |
| Files | 12 |
| Dependencies | no manifest (README lists fastapi, uvicorn, pydantic, pytest, httpx) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] No dependency manifest (requirements.txt / pyproject.toml) — deps only in README prose.
2. [info] Validation returns 422 where R9's how_to_verify names 400 (422 is FastAPI-idiomatic; noted for cross-run consistency).

No critical/high/medium findings. All 12 pinned requirements implemented with passing tests.

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                                   # cached mechanical scores
grep -rE "pytest\.skip|xfail" tests/ | wc -l      # 0 skips
pytest tests/ -v                                  # 15 pass (build+test signal)
```
