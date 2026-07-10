# Evaluation: agent=hermes-local_language=python_prompt=ATDD · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (FastAPI), prompt=ATDD
- **Status:** ok
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R11 README)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — code_quality=0.83, maintainability=0.92, idiomatic=0.88 (scores.json); 3 deprecated-API warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items). Mechanical signal: `test_coverage=0.68`, `defect_rate=1.0` ⇒ build + all 20 tests pass.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:36 create_book`, persists via `BookModel` |
| R2 | GET /books lists all | ✓ implemented | `app.py:58 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:62-63` filters by author; `test_app.py:114` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:72 get_book`, 404 at `:78`; `test_app.py:154` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:85 update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:109 delete_book`, 204 |
| R7 | Stored in SQLite | ✓ implemented | `models.py:11-14` `sqlite:///books.db` via SQLAlchemy |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/404/422 across routes; `app.py:36,109,78` |
| R9 | Validation: title & author required | ✓ implemented | `models.py:50-51` `Field(min_length=1)` → 422; `test_app.py:74-92` |
| R10 | GET /health | ✓ implemented | `app.py:27 health_check` returns `{"status":"ok"}` |
| R11 | README.md with setup/run | ✗ missing | no README.md in run_dir |
| R12 | ≥3 unit/integration tests | ✓ implemented | 20 tests in `test_app.py`, coverage 0.68 > 0 |

**Prompt (ATDD) conformance:** Strong. `test_app.py` drives the service only through FastAPI `TestClient` over HTTP, uses domain-language names (`test_create_book_...`, `test_list_books_filtered_by_author_...`), and each test starts from an empty service via an `autouse` reset fixture. One deviation: the reset fixture (`test_app.py:16-20`) reaches into `models.delete_db()/init_db()` — back-door DB access the ATDD prompt explicitly discourages (see finding `P1-backdoor`).

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill step 2):

```text
test_coverage = 0.68   # build + all 20 tests pass; 68% line coverage
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.83   maintainability = 0.92   idiomatic = 0.88
```

```text
20 acceptance tests, 0 skipped, 0 xfail (grep of test_app.py)
Uncovered lines: app.py:95-96 (no-op update early return), app.py:141-143 (__main__)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app+models) | 217 |
| Lines of code (tests) | 228 |
| Files (excl. artifacts) | 4 |
| Dependencies | 5 (fastapi, uvicorn, pydantic + pytest, httpx) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] R11 — No README.md shipped (required deliverable)
2. [low] P1-backdoor — Test reset fixture uses back-door DB access, contrary to ATDD prompt
3. [low] lint-deprecated — Deprecated `@app.on_event`, `Session.query().get()`, `datetime.utcnow()`
4. [info] coverage-68 — Line coverage 68%; all tests pass

## Reproduce

```bash
cd "experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=ATDD/rep3"
cat scores.json                                   # mechanical scores (no re-run)
grep -cE "def test_" test_app.py                  # 20 tests
grep -rnE "pytest\.skip|xfail" test_app.py        # 0 skips
ls README*                                        # absent → R11 missing
```
