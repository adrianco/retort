# Evaluation: agent=codex language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-luna, prompt=neutral, framework=Flask (inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — test_coverage=0.91, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:82` `create_book` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:99` `list_books` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:106` `WHERE author LIKE ?`; test `test_list_can_filter_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:114` `get_book` returns row or `error(...,404)` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:119` `update_book` partial validation + UPDATE |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:145` `delete_book` returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:32` `sqlite3.connect`; schema `app.py:11` |
| R8 | JSON responses with appropriate HTTP codes | ✓ implemented | 201/200/404/400/204 across handlers; `jsonify` throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:63` `validate_fields`; test `test_required_fields_are_validated` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:78` `health` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — venv, install, `flask --app app run`, endpoints, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_app.py` — 4 tests via `test_client` |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate output):

```text
test_coverage = 0.91   (tests executed and passed; 91% line coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.79
maintainability = 0.80   idiomatic = 0.69
```

Test suite (`tests/test_app.py`), all passing, none skipped:

```text
test_health_and_create_book
test_list_can_filter_by_author
test_update_and_delete_book
test_required_fields_are_validated
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~200 (app.py 161, test_app.py 40) |
| Files (source) | 4 (app.py, tests/test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — both informational, no deductions:

1. [info] `?author=` filter uses substring `LIKE` match, not exact equality (`app.py:107`)
2. [info] GET /books returns the full collection with no pagination (`app.py:104`)

No critical, high, medium, or low findings. All 12 pinned requirements implemented and
tested; no build/test failures; no skipped or disabled tests.

Note: the agent hit one sandbox rejection during the run (`rm -rf` blocked, see
`_agent_stderr.log`) but recovered — it did not affect the delivered artifacts.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-53-codex-bookshop/runs/agent=codex_language=python_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (build/test/lint)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                # 4 tests, all pass
```
