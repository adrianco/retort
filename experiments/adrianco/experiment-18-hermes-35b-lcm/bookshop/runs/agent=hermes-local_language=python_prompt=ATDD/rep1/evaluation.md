# Evaluation: agent=hermes-local language=python prompt=ATDD · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Prompt (ATDD):** followed — external-client acceptance suite drives the design; one minor deviation (back-door DB reset in setup)
- **Tests:** 35 passed / 0 failed / 0 skipped (35 effective) — `test_coverage=0.97`, `defect_rate=1.0` from `scores.json`
- **Build:** pass — tests execute (`test_coverage=0.97`); not re-run
- **Lint:** pass — `code_quality=0.83` from `scores.json`; not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:38-72`; `test_create_book_returns_201` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:74-94`; `test_list_contains_created_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:77-81` (`ilike` partial); `test_list_filter_by_author_returns_matching` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:96-108`; `test_get_nonexistent_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:110-148`; `test_update_existing_book_changes_data` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:150-158`; `test_delete_existing_book_removes_it` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:19-29` Flask-SQLAlchemy `sqlite:///books.db`; `instance/books.db` present |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...)`, 201/200/404/400 throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:52-55`; `test_create_book_missing_title_returns_400`, `_missing_author_` |
| R10 | GET /health | ✓ implemented | `app.py:33-36`; `test_health_status_is_healthy` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md:11-24` (setup+run); minor test-count inaccuracy (DOC1) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 35 tests (27 acceptance + 8 unit); `test_coverage=0.97` |

### Prompt (ATDD) conformance

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests: external client, public REST only, no back-door to internals/DB | ~ partial | Assertions are black-box over HTTP (`tests/test_acceptance.py`), but the autouse fixture resets state via `_db_module.drop_all()/create_all()` (`:38-44`) — a back-door reset |
| P2 | Assert WHAT not HOW, domain language, atomic & independent from empty service | ✓ implemented | Domain-named scenarios; autouse `_clear_db` gives each test an empty store (`:38-44`) |
| P3 | Tests fail first, then drive implementation; unit TDD underneath | cannot-verify | Red-first process not recoverable from the archive; unit layer does exist (`tests/test_unit.py`) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json: test_coverage=0.97  defect_rate=1.0  code_quality=0.8333
             maintainability=0.9886  idiomatic=0.80  token_efficiency=0.0098
```

```text
pytest tests/ -v   (per agent stdout, not re-run)
35 passed in ~0.20s  (27 acceptance + 8 unit); 0 failed, 0 skipped
grep skip/xfail in tests/ = 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py) | 197 |
| Lines of code (tests) | 412 |
| Files (excl. instance/, __pycache__) | 15 |
| Dependencies (requirements.txt) | 4 |
| Tests total | 35 |
| Tests effective | 35 |
| Skip ratio | 0% |
| Build/test duration | ~0.20s (reported) |

## Findings

All 4 findings are ≤ medium (no requirement is missing or partial against the spec):

1. [medium] CQ1 — `create_app()` always provisions persistent `instance/books.db` even under test (config read after factory construction)
2. [low] P1 — ATDD acceptance tests use a back-door DB reset in setup
3. [low] DOC1 — README undercounts unit tests (says 5, actual 8)
4. [low] CQ2 — `Book.to_dict()` defined but route handlers hand-roll the same dict

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=ATDD/rep1
cat scores.json                                   # mechanical scores (not re-run)
grep -rEc "def test_" tests/*.py                  # 27 + 8 = 35
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ | wc -l   # 0
python3 -c "import sqlite3;print(sqlite3.connect('instance/books.db').execute('SELECT count(*) FROM books').fetchall())"  # [(0,)]
# full run: python -m pytest tests/ -v
```
