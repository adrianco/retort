# Evaluation: agent=hermes-local language=python model=mlxlocal/Qwen3.6-35B-A3B prompt=neutral stack=m35 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/Qwen3.6-35B-A3B, framework=Flask, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.79` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (R1–R12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:56-85` create_book, INSERT with all 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:88-102` list_books, SELECT * → JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:94-98` `WHERE author LIKE %author%`; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:105-112` get_book, 404 on None |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:115-147` update_book, UPDATE + re-select; partial updates supported |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:150-160` delete_book, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,15,31-42` sqlite3, `books.db`, WAL mode |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/400/404 codes |
| R9 | Validation: title and author required | ✓ implemented | `app.py:66-69` reject blank title/author with 400; tests cover both |
| R10 | GET /health health check | ✓ implemented | `app.py:50-53` returns `{status: healthy}` 200 |
| R11 | README.md with setup + run instructions | ✓ implemented | `README.md` — pip install, `python app.py`, endpoint docs |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 18 tests, `test_coverage=0.98` |

No prompt-factor requirements: `prompt=neutral` is a tone-only prompt with no additional checkable instructions.

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 0.98   → build + tests passed (near-full coverage)
defect_rate   = 1.0    → build + test succeeded
code_quality  = 0.79   → lint/quality pass
maintainability = 1.0
idiomatic     = 0.72
```

Agent's own report (`_agent_stdout.log`): "Test results: 18/18 passed".
Skip scan of `test_app.py`: 0 skips / xfails.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py) | 168 total / 127 non-blank |
| Lines of code (tests, test_app.py) | 225 total / 184 non-blank |
| Files (excl. artifacts) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 2 (flask, pytest) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — no critical/high/medium/low items:

1. [info] PUT supports partial updates beyond spec — `app.py:127-138`
2. [info] `?author=` filter uses substring LIKE match, not exact equality — `app.py:96`
3. [info] code_quality 0.79, minor lint/style — `scores.json`

## Reproduce

```bash
cd "experiment-28-rebaseline-sampling/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep1"
cat scores.json                                 # mechanical scores (not re-run)
grep -cE "def test_" test_app.py                # 18
grep -rnE "pytest\.skip|xfail" test_app.py      # 0
# To actually run tests: python -m pytest test_app.py -v
```
