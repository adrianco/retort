# Evaluation: agent=codex language=python model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=0.88`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:44-53` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:39-40` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:41-42` WHERE author = ? |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:59-62`; `not_found` at 122 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:63-73` UPDATE, 404 on rowcount 0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:74-79` DELETE, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15-25` sqlite3.connect + CREATE TABLE |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `respond()` at 113-118; 201/200/204/400/404/405/500 |
| R9 | Input validation: title and author required | ✓ implemented | `read_book` at 100-103 raises → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:32-33` returns `{status:"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Run / Endpoints / Tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 3 tests; `test_coverage=0.88` |

No prompt-factor requirements (prompt=neutral is not a `prompts/<level>.md` instruction set for this task).

## Build & Test

Build/test not re-run — using stored mechanical scores (per skill Step 2):

```text
scores.json
test_coverage = 0.88   (build succeeded; tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
maintainability = 0.8830
idiomatic     = 0.70
```

Skip scan (`tests/*.py`): 0 skips / xfails found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 128 (`app.py`) + 49 (tests) = 177 |
| Files | 2 source (app.py, tests/test_api.py) + README |
| Dependencies | 0 (Python stdlib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Beyond-spec HTTP correctness: Location, Allow, 405 and 500 handling
2. [info] Stricter validation than required (year int, isbn str type checks)

No requirement gaps, build/test failures, or skipped tests.

## Reproduce

```bash
cd experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep2
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
grep -rE "^def test_" tests/*.py | wc -l
# optional: python -m pytest
```
