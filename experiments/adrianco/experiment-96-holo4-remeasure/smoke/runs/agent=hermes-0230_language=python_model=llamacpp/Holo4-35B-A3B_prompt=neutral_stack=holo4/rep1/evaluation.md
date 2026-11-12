# Evaluation: agent=hermes-0230 language=python model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0230, model=llamacpp/Holo4-35B-A3B, prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `smoke/REQUIREMENTS.json`, R1–R12)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — from stored scores (`scores.json`), not re-run
- **Lint:** pass — code_quality=0.79 (stored)
- **Architecture:** `run-summary` skill unavailable in this environment; see app.py (single-module Flask + sqlite3 CRUD)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (from `scores.json`, not re-run): `test_coverage=0.93`, `defect_rate=1.0`
(build+test succeeded), `code_quality=0.789`, `maintainability=1.0`, `idiomatic=0.30`,
`token_efficiency=0.0089`. Prompt factor `neutral` is non-prescriptive (no testing
methodology required), so it adds no checkable `P*` requirements beyond R12.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `app.py:46-78` create_book; INSERT at :70-74; test_create_book `test_app.py:30` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:81-89` list_books; test_list_books `test_app.py:66` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:83-86` filters on `author` query param; `test_app.py:90-94` asserts filtered count |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:92-98`; 404 at :96-97; test_get_book_not_found `test_app.py:110` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:101-135`; test_update_book `test_app.py:115` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:138-146` returns 204; test_delete_book `test_app.py:133` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,12` sqlite3.connect; schema `app.py:27-37` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | jsonify + 201/200/404/400/204 throughout `app.py:43-146` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:55-58` reject missing/blank → 400; test_create_book_missing_* `test_app.py:44,55` |
| R10 | GET /health health check | ✓ implemented | `app.py:41-43` returns `{"status":"ok"}` 200; test_health `test_app.py:23` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` setup, run, endpoints, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 tests in `test_app.py`; test_coverage=0.93 (>0) |

## Build & Test

Not re-run — stored scores used per skill (compiled/interpreted build already ran during scoring):

```text
scores.json: test_coverage=0.93  defect_rate=1.0  code_quality=0.789
→ build + all tests passed; 93% line coverage; no skipped/disabled tests
_agent_stdout.log: "All 9 unit/integration tests pass"
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + test_app.py) | 305 |
| Files (source: .py/.md/.txt) | 5 |
| Dependencies (requirements.txt) | 2 (flask, pytest) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| test_coverage (stored) | 0.93 |
| API calls / total tokens | 25 / 543,861 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Autouse `client` fixture's yielded test client is unused — tests call `app.test_client()` directly (`test_app.py:17`)
2. [info] Idiomatic score low (0.30) despite clean, working code (`.idiomatic_cache.json`)
3. [info] `init_db()` runs at import time, creating `books.db` as an import side effect (`app.py:159`)

No critical/high/medium findings — a clean, spec-complete, passing run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-96-holo4-remeasure/smoke/runs/agent=hermes-0230_language=python_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep1"
cat scores.json            # stored mechanical scores (build/test/lint) — not re-run
pytest test_app.py -v      # optional: 9 tests, all pass
```
