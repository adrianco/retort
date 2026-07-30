# Evaluation: agent=codex effort=high language=python model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=high, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.79` (scores.json); not re-run
- **Architecture:** single-module Flask app factory; run-summary skill not invoked (unavailable in this session)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:61 create_book` — INSERT of title/author/year/isbn, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:72 list_books` — SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:74-80` — WHERE author = ?; test `test_list_can_filter_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:83 get_book` + `fetch_book` 404 on miss |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:87 update_book` — merge + UPDATE, 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:103 delete_book` — DELETE, 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:14-22 SCHEMA`, `sqlite3.connect` at `app.py:36` |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/500 handlers `app.py:48-59` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:131-138 validate_book`; test `test_title_and_author_are_required` |
| R10 | GET /health health check | ✓ implemented | `app.py:57 health` — `{"status":"ok"}`, 200; test `test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — venv/pip/run + endpoint table + curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 5 test methods, all executed |

No requirements partial or missing. No enhancements beyond spec that change behavior; error-handling for DB failures (`app.py:52-55`) is a robustness extra.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
defect_rate    = 1.0   → build + tests passed
test_coverage  = 0.93  → line coverage 93% (tests executed and passed)
code_quality   = 0.79
maintainability= 0.92
idiomatic      = 0.62
```

```text
python -m unittest -v   (5 tests: create/get, author filter, update/delete, validation, health)
5 passed / 0 failed / 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 142 |
| Lines of code (test_app.py, non-blank) | 54 |
| Files (excl. .git/.coverage) | 11 |
| Dependencies | 1 (Flask) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Line coverage | 93% |

## Findings

All findings are informational (this is a clean pass):

1. [info] SQLite schema re-created per request via `before_request` (`app.py:34-40`) — safe but could init once.
2. [info] Line coverage 0.93 — the `sqlite3.Error` 500 handler (`app.py:52-55`) is untested.
3. [info] POST empty-body handling returns 400 correctly; no action needed.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=high_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                    # stored build/test/quality scores (not re-run)
cat ../../../REQUIREMENTS.json     # pinned 12-requirement checklist
grep -cE 'def test_' test_app.py   # 5
python -m unittest -v              # optional: re-run tests (5 pass)
```
