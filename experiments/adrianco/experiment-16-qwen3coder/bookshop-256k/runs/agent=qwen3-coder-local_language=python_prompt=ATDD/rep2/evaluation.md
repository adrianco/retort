# Evaluation: agent=qwen3-coder-local language=python prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=FastAPI (inferred), prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — coverage 67%
- **Build:** pass — `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this environment; see Build & Test / Metrics below
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 6 low)

Mechanical scores read from `scores.json` (inline gate; DB not re-queried, toolchain not re-run):
`test_coverage=0.67, code_quality=0.833, defect_rate=1.0, maintainability=0.623, idiomatic=0.58, token_efficiency=0.0074`.

## Requirements

Checklist is the pinned `bookshop-256k/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:62 create_book`; `test_book_api.py:32 test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:100 get_books`; `test_book_api.py:72 test_get_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:106-107`; `test_book_api.py:91 test_get_all_books_filtered_by_author` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:124 get_book`; `test_book_api.py:117,135` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:145 update_book`; `test_book_api.py:140,165` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:214 delete_book`; `test_book_api.py:172,188` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:32 init_db`, `sqlite3` + `books.db` |
| R8 | JSON responses + correct codes | ✓ implemented | `app.py:62 status_code=201`, 404/400 raised throughout |
| R9 | Validation: title & author required | ✓ implemented | Pydantic required fields (`app.py:20 BookCreate`); rejected with 422 — `test_book_api.py:50,61` (see finding: how_to_verify expects 400) |
| R10 | GET /health | ✓ implemented | `app.py:57 health_check`; `test_book_api.py:26 test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md:19-34` setup + run + `pytest` |
| R12 | ≥3 unit/integration tests | ✓ implemented | 15 tests across `test_book_api.py` + `unit_tests.py`; `test_coverage=0.67 > 0` |

**Prompt (ATDD) conformance:** Acceptance tests exist at the HTTP boundary via FastAPI `TestClient`, asserting on domain behavior (create/list/filter/update/delete/reject-missing-title) — consistent with the ATDD prompt. Deviation: setup deletes `books.db` and calls `init_db()` directly (back-door DB access), which the prompt explicitly forbids — see finding `P1-backdoor-db`.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: defect_rate=1.0  => build + tests succeeded
             test_coverage=0.67 => 67% coverage, 15/15 tests effective, 0 skips
             code_quality=0.833 (lint/quality gate)
```

```text
grep skip/xfail in test_book_api.py, unit_tests.py -> 0
def test_* count -> 15  (12 in test_book_api.py, 3 in unit_tests.py)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 238 |
| Lines of code (tests) | 267 (test_book_api.py 190 + unit_tests.py 77) |
| Debug/scaffolding LOC (non-deliverable) | 145 (demo.py 96, detailed_debug.py 31, debug_test.py 18) |
| Files (excl. artifacts) | 13 |
| Dependencies | no manifest (README: fastapi, uvicorn) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Coverage | 67% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] ATDD acceptance tests use back-door DB access for setup (`test_book_api.py:11-15`, `unit_tests.py:11-14`)
2. [low] SQLite connection leaked on update 404 path (`app.py:152-156`)
3. [low] SQLite connection leaked on delete 404 path (`app.py:220-225`)
4. [low] Debug/scaffolding scripts left in workspace (`debug_test.py`, `detailed_debug.py`, `demo.py`)
5. [low] Validation returns 422 but README/how_to_verify document 400 (`app.py`/`README.md:112`)

No critical or high findings: the run implements all 12 requirements, builds, and passes all 15 tests with no skips.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=python_prompt=ATDD/rep2
cat scores.json                 # stored mechanical scores (no re-run)
grep -rEc "pytest\.skip|xfail" test_book_api.py unit_tests.py
grep -rE "^def test_" test_book_api.py unit_tests.py | wc -l
# (optional) re-run tests: pip install fastapi uvicorn pytest httpx && pytest -q
```
