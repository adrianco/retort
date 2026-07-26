# Evaluation: effort=default·language=python·model=claude-opus-4-8·prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8, prompt=neutral, effort=default (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — from `test_coverage=0.96`, `defect_rate=1.0`
- **Build:** pass (Flask import + tests ran) — from scores.json
- **Lint:** pass — `code_quality=0.79` from scores.json
- **Architecture:** single-module Flask app (`app.py`) + `test_app.py`; `run-summary` skill not generated (2-file codebase, trivial structure)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:108` create_book INSERTs all 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:129` list_books returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:132-136` filters by author param; `test_app.py:55` test_list_and_author_filter |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:141` get_book, 404 if absent; `test_app.py:98` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:149` update_book merges + persists; `test_app.py:70` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:173` delete_book, 204/404; `test_app.py:84` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8,24-41` stdlib sqlite3, books table, books.db file |
| R8 | JSON responses + correct status codes | ✓ implemented | `app.py` jsonify throughout; 201/200/204/400/404 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:54-89` _validate_payload; `test_app.py:46` test_create_requires_title_and_author |
| R10 | GET /health endpoint | ✓ implemented | `app.py:104-106` returns {"status":"ok"}; `test_app.py:28` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, run, endpoints, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 tests in `test_app.py`, 0 skipped, test_coverage=0.96 |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and adds no checkable requirements — no P-requirements.

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.96   -> build succeeded, all tests executed and passed
defect_rate   = 1.0    -> build+test succeeded
code_quality  = 0.789
maintainability = 0.972
idiomatic     = 0.92
```

Tests (`test_app.py`, static count): 9 test functions, 0 skips/xfail.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py) | 189 |
| Lines of code (tests) | 100 |
| Files | 12 (incl. .coverage, caches, logs) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top items (full list in `findings.jsonl`) — none at or above medium severity:

1. [low] PUT with no valid fields returns 400 rather than a no-op 200 (defensible; R5 fully implemented)
2. [info] GET /books has no pagination (not required)
3. [info] No uniqueness constraint on isbn (not required)

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=default_language=python_model=claude-opus-4-8_prompt=neutral/rep3"
cat scores.json
cat ../../../REQUIREMENTS.json
grep -cE "^def test_" test_app.py
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
```
