# Evaluation: agent=hermes-local language=python prompt=TDD · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=TDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Prompt (TDD):** satisfied at end-state — test-first structure, thorough coverage (process not independently verifiable, no git history)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective)
- **Build:** pass — `test_coverage=0.98`, `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:58 create_book` inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:44 list_books` returns all rows as JSON |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:49-53` LIKE filter; `test_books.py:23,38` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:76 get_book` returns 404 when absent |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:85 update_book`; `test_books.py:126` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:110 delete_book`; `test_books.py:150` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15 init_db`, raw sqlite3, `books` table |
| R8 | JSON responses + status codes | ✓ implemented | jsonify + explicit 200/201/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:62-65` returns 400; `test_books.py:101,109` |
| R10 | GET /health | ✓ implemented | `app.py:39 health` returns `{"status":"ok"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Running, API, Tests sections |
| R12 | ≥3 tests | ✓ implemented | 20 tests across `test_books.py`/`test_health.py` |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.98   (build + tests executed; all pass, ~98% line coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.833
maintainability = 1.0
idiomatic     = 0.85
```

```text
pytest tests/ -v
20 tests collected — 20 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 127 |
| Lines of code (tests) | 262 |
| Files (source, excl. artifacts) | 15 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Coverage | ~98% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] PUT /books/{id} assumes a JSON body — bodyless PUT raises 500 (`app.py:93`)
2. [low] Per-request DB connections never closed — no teardown hook (`app.py:7`)
3. [low] README mislabels author filter as case-sensitive (`README.md:61`)
4. [info] DB path threaded through process-global `os.environ` (`app.py:33`)

No critical, high, or medium findings. All 12 spec requirements met; tests pass with no skips.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=TDD/rep1
cat scores.json                       # stored mechanical scores
grep -rE "pytest\.skip|xfail" tests/  # skip check (0)
python -m pytest tests/ -v            # 20 passed (fallback only; scores already stored)
```
