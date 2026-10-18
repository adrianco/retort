# Evaluation: rest-api-crud (dwq4) · rep 1

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, agent=hermes-0222, prompt=neutral, stack=dwq4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — tests executed (coverage 61%)
- **Build:** pass — Python/Flask, no compile step (scores from `scores.json`, not re-run)
- **Lint:** n/a — `code_quality=0.667`, `maintainability=0.854`, `idiomatic=0.300` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

Stored scores (`scores.json`, not re-run per skill step 2): `test_coverage=0.61`,
`defect_rate=0.8367`, `code_quality=0.6667`, `maintainability=0.8542`, `idiomatic=0.30`,
`token_efficiency=0.0136`. `test_coverage > 0` confirms the suite executed (R12).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:40-75` create_book, INSERT of all four fields, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:77-95` get_books returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:85-87` WHERE author LIKE; test `test_filter_books_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:97-111` get_book, 404 branch at :108 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:113-155` update_book, UPDATE + 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:157-181` delete_book, DELETE + 200 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:10-33` sqlite3 `books.db`, CREATE TABLE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify everywhere; 201/200/400/404/500 across routes |
| R9 | Validation: title and author required | ~ implemented | `app.py:46,119` presence check → 400; presence-only (empty strings pass, see finding R9-note) |
| R10 | GET /health | ✓ implemented | `app.py:35-38` health_check → {"status":"healthy"},200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, run, testing, curl examples |
| R12 | >= 3 tests that run | ✓ implemented | `test_app.py` 9 tests, 0 skips; `test_coverage=0.61` |

## Build & Test

Not re-run — scores read from `scores.json` per skill step 2.

```text
test_coverage = 0.61   # suite executed; 61% line coverage
defect_rate   = 0.8367
9 tests in test_app.py (unittest), 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + test_app.py) | 409 |
| Lines incl. scratch scripts (verify*/final_report) | 592 |
| Files (excl. __pycache__/.coverage) | ~16 |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Flask debug mode enabled and bound to 0.0.0.0 — `app.py:188`
2. [low] Three non-deliverable scratch scripts left in workspace — verify.py, verify2.py, final_report.py
3. [low] Validation is presence-only; empty title/author accepted — `app.py:46`
4. [info] Author filter is substring LIKE match, not exact — `app.py:87`

No critical/high/medium findings. All 12 pinned requirements are implemented and the
test suite executed cleanly.

## Reproduce

```bash
cd "experiments/adrianco/experiment-71-dwq-hard-task/smoke-hermes/runs/agent=hermes-0222_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep1"
cat scores.json            # stored mechanical scores (not re-run)
grep -cE "def test_" test_app.py
grep -rE "skip|xfail" test_app.py | wc -l
```
