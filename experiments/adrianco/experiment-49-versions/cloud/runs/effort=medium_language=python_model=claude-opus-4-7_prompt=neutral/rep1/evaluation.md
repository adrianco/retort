# Evaluation: effort=medium_language=python_model=claude-opus-4-7_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-7, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — (no build step; import/collection succeeded, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.789 from scores.json
- **Architecture:** single-module Flask app (`app.py`) with an app-factory `create_app(database=...)`, per-context SQLite connection, five `/books` CRUD routes plus `/health`.
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:46-70` create_book, INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:72-82` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:75-79` filters by author param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:84-90` returns 404 if absent |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:92-122` merge-update + 200 |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:124-132` DELETE + 204 |
| R7 | SQLite persistence | ✓ implemented | `app.py:11` sqlite3.connect; CREATE TABLE `app.py:13-23` |
| R8 | JSON + status codes | ✓ implemented | jsonify + 200/201/204/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:51-54`, `app.py:104-107` (POST + PUT) |
| R10 | GET /health | ✓ implemented | `app.py:42-44` returns {"status":"ok"} 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, tests |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 8 test methods, all pass |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill):

```text
test_coverage = 0.94   # coverage; tests executed and passed
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.789
maintainability = 1.0
idiomatic     = 0.72
```

```text
python3 -m unittest -v   # 8 tests: health, create+get, missing title, missing
                         # author, list+filter, update, update-missing(404), delete
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 227 (app.py 138 + test_app.py 89) |
| Files | 4 (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 1 (Flask) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] SQLite persistence uses per-request connection with lazy schema creation — meets R7.
2. [info] PUT does partial update by merging with current row — exceeds spec.

No correctness, requirement, or test-integrity defects found. Clean run.

## Reproduce

```bash
cd runs/effort=medium_language=python_model=claude-opus-4-7_prompt=neutral/rep1
cat scores.json                 # stored mechanical scores
python3 -m unittest -v          # 8 tests (only if re-verifying)
grep -cE "def test_" test_app.py
```
