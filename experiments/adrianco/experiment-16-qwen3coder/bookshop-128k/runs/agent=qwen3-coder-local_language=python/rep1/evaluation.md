# Evaluation: bookshop-128k · agent=qwen3-coder-local language=python · rep 1

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (Flask, inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — coverage 0.92
- **Build:** pass — `test_coverage=0.92`, `defect_rate=1.0` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:37` `create_book` inserts (title, author, year, isbn), returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:76` `get_books` returns collection (200) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:79,85-89` LIKE filter on author; `test_get_books_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:106` returns book or 404 (`app.py:116-117`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:124` `update_book`, 404 when rowcount 0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:164` `delete_book`, 404 when rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,10-24` `sqlite3` + `books` table on disk |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` everywhere; 201/200/404/400/500 across routes |
| R9 | Validation: title & author required | ✓ implemented | `app.py:43,130` reject missing fields with 400; `test_create_book_missing_fields` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:32-35` returns `{"status":"healthy"}` 200; `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, per-endpoint curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 `def test_*` in `test_app.py`; `test_coverage=0.92 > 0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.92   (build + tests executed; 11 tests, all passing)
defect_rate   = 1.00   (build + test succeeded)
code_quality  = 0.79
maintainability = 0.98
idiomatic     = 0.68
```

Skip scan: `grep -rE "@unittest.skip|self.skipTest|pytest.skip|xfail" *.py` → 0 skips. All 11 tests are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 423 (app.py 184 + test_app.py 239) |
| Files | 9 (excl. .git, agent stdout log, .coverage) |
| Dependencies | 1 (Flask; no manifest) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] README curl examples use port 5000 but the app serves 5001 (`README.md:37-81` vs `app.py:185`)
2. [low] No dependency manifest (requirements.txt / pyproject.toml)
3. [low] Flask debug mode enabled in the run entrypoint (`app.py:185`)
4. [info] ISBN UNIQUE constraint + duplicate handling beyond spec (enhancement)

No requirement gaps and no build/test failures — this run cleanly conforms to the spec.

## Reproduce

```bash
cd "experiment-16-qwen3coder/bookshop-128k/runs/agent=qwen3-coder-local_language=python/rep1"
cat scores.json                                   # stored mechanical scores
grep -rE "@unittest.skip|self.skipTest" *.py | wc -l   # skip scan → 0
wc -l app.py test_app.py README.md                # LOC
# (build/test not re-run — test_coverage=0.92, defect_rate=1.0 already stored)
```
