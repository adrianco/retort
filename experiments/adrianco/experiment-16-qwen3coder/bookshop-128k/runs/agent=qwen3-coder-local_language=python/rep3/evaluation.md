# Evaluation: bookshop-128k · agent=qwen3-coder-local language=python · rep 3

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (Flask chosen by agent)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 tests, 0 skipped (11 effective); test_coverage=0.9, defect_rate=1.0 from `scores.json`
- **Build:** pass — from `scores.json` (defect_rate=1.0 ⇒ build+tests succeeded; not re-run)
- **Lint:** pass — code_quality=0.7889 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 3 low, 1 info)

## Requirements

Checklist is the pinned `bookshop-128k/REQUIREMENTS.json` (constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:39-78` create_book, INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:80-104` get_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:83,89-92` WHERE author=? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:106-122`, 404 at :117 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:124-168` UPDATE, 404 at :149 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:170-188`, 404 at :180 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,12-26` sqlite3 + books table |
| R8 | JSON + correct status codes | ✓ implemented | jsonify throughout; 201/200/400/404/500 |
| R9 | Validation: title+author required | ✓ implemented | `app.py:45-46` and PUT `:130-131` → 400 |
| R10 | GET /health | ✓ implemented | `app.py:34-37` returns {status: healthy} 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup + run + usage |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 11 test methods, coverage 0.9 |

## Build & Test

Not re-run — scores read from `scores.json` (skill step 2):

```text
scores.json: {"code_quality": 0.789, "token_efficiency": 0.0104,
              "test_coverage": 0.9, "defect_rate": 1.0,
              "maintainability": 0.976, "idiomatic": 0.7}
```

- `defect_rate=1.0` ⇒ build + tests executed and passed.
- `test_coverage=0.9` ⇒ tests ran with high coverage.
- No skipped/disabled tests: `grep -E "skip|xfail" *.py` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py+test_app.py) | 192 + 239 = 431 |
| Files (excl. artifacts/logs) | 9 tracked (app, tests, req, README, start.sh, stack/meta/scores + summary) |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| test_coverage (scored) | 0.90 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Tests operate on the app's real default `books.db` — no isolated temp DB (`test_app.py:15`, `app.py:10`)
2. [low] No type validation on year/isbn inputs (`app.py:50-51`)
3. [low] `conn` referenced in except before guaranteed assignment (`app.py:73-78`, `:163-168`)
4. [info] ISBN uniqueness enforced and surfaced as 400 — enhancement (`app.py:22,73-75`)

No critical or high findings: all 12 requirements implemented, tests pass, no skips.

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-128k/runs/agent=qwen3-coder-local_language=python/rep3
cat scores.json                                   # stored build/test/lint scores
grep -cE "def test_" test_app.py                  # 11
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail|unittest\.skip" *.py  # 0
# build/test NOT re-run — defect_rate=1.0 in scores.json is authoritative
```
