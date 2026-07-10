# Evaluation: agent=qwen3-coder-local language=python · rep 2

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (FastAPI in practice)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 pytest + 1 smoke script, all passed / 0 failed / 0 skipped (12 effective) — coverage 62%
- **Build:** pass (import + tests executed; `defect_rate=1.0` from `scores.json`)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 3 info)

Mechanical scores (from `scores.json`): test_coverage=0.62, code_quality=0.833, defect_rate=1.0, maintainability=0.791, idiomatic=0.58, token_efficiency=0.0075.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:85 create_book` INSERT; `tests.py:25 test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `main.py:109 read_books`; `tests.py:52 test_read_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:65-70 get_books` LIKE; `tests.py:68 test_read_books_with_filter` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.py:114 read_book` + 404; `tests.py:93,110` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.py:125 update_book`; `tests.py:114 test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.py:174 delete_book`; `tests.py:140 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `main.py:34-47 init_db` sqlite3; `books.db` |
| R8 | JSON + appropriate status codes | ✓ implemented | 201 `main.py:85`, 404 `main.py:119`, 200 responses |
| R9 | Validation: title & author required | ✓ implemented | `BookCreate main.py:21-25` (required → 422) + `main.py:88` 400 guard; see finding R9-code |
| R10 | GET /health | ✓ implemented | `main.py:80 health_check`; `tests.py:20 test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` install + run + endpoints |
| R12 | ≥3 tests | ✓ implemented | 11 pytest functions in `tests.py`; test_coverage=0.62>0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (test gate already executed during scoring):

```text
defect_rate=1.0   → build/import + tests executed and passed
test_coverage=0.62 → 62% line coverage, tests ran (>0)
code_quality=0.833
```

Test inventory (static): 11 `test_*` functions in `tests.py` + `test_all_endpoints` in `test_api.py`; 0 skips/xfails detected.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 441 (main 192, tests 159, smoke 90) |
| Files | 5 source (+ README, DB) |
| Dependencies | fastapi, uvicorn (no manifest — README-only) |
| Tests total | 12 (11 pytest + 1 smoke) |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl` — none reach high/critical):

1. [low] Validation returns 422 for missing title/author, not the spec's 400 (`main.py:88`)
2. [low] Explicit empty-field 400 guard reachable only for empty strings (`main.py:88-92`)
3. [low] No requirements.txt / pyproject pinning fastapi+uvicorn (README-only install)
4. [info] SQLite `books.db` committed into workspace
5. [info] Synchronous sqlite3 calls inside async handlers

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-128k/runs/agent=qwen3-coder-local_language=python/rep2
cat scores.json                 # mechanical scores (test gate already ran)
python -m pytest tests.py       # 11 tests
python test_api.py              # end-to-end smoke walk
```
