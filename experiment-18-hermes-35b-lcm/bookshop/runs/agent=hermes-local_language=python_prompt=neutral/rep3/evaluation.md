# Evaluation: agent=hermes-local · language=python · prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=Flask, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`, R1–R12)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — from `scores.json` (defect_rate=1.0; tests import & run)
- **Lint:** n/a — code_quality=0.7889 from `scores.json`
- **Coverage:** test_coverage=0.88 from `scores.json`
- **Architecture:** flat single-module Flask app — `app.py` (Book model + 6 routes + health), `test_app.py` (pytest client fixture + 12 tests), `README.md`. (run-summary skill not registered as invocable here; codebase is a trivial 2-file module — no `summary/` generated.)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `app.py:46-73` create_book; test `test_create_book` |
| R2 | GET /books list all | ✓ implemented | `app.py:76-88` list_books; test `test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:81-84` ilike substring filter; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:91-99`; tests `test_get_book_by_id`, `test_get_book_not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:102-133`; tests `test_update_book`, `test_update_nonexistent_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:136-147`; tests `test_delete_book`, `test_delete_nonexistent_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8` `sqlite:///books.db`; `books.db` present. Caveat: `init_db` drops on startup — see finding F1 |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...), 201/200/400/404` throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:57-61`; tests `test_create_book_missing_title`, `test_create_book_missing_author` |
| R10 | GET /health | ✓ implemented | `app.py:40-43`; test `test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, endpoints, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 tests in `test_app.py`; test_coverage=0.88 |

Prompt factor `neutral` is a no-op ("no particular methodology prescribed") — no additional checkable `P*` requirements.

## Build & Test

Not re-run — mechanical scores taken from `scores.json` (inline gate):

```text
scores.json: test_coverage=0.88  defect_rate=1.0  code_quality=0.7889
             maintainability=1.0  idiomatic=0.58   token_efficiency=0.0115
_agent_stdout.log: "Tests: 12/12 passed"
```

Skip scan: `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail"` → 0 matches. Effective tests = 12.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py + test_app.py) | 390 |
| Source files | app.py, test_app.py, README.md |
| Dependencies | flask, flask-sqlalchemy (unpinned; no requirements.txt) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Coverage | 88% |
| Agent tokens (total) | 520,148 (19 API calls, Qwen3.6-35B-A3B) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] F1 — `init_db()` runs `db.drop_all()` on every startup (`app.py:36`), wiping persisted books each `python app.py` launch.
2. [low] F2 — PUT author update strips before `str()` coercion (`app.py:123`); non-string author → 500.
3. [low] F3 — Dead unused `make_client` generator in tests (`test_app.py:11-27`).
4. [low] F4 — No pinned dependency file (`requirements.txt`).
5. [info] F5 — 12 tests provided vs 3 required; all pass.

No critical or high findings — a clean run that implements the full spec with passing tests.

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep3
cat scores.json _meta.json               # mechanical scores (not re-run)
grep -c '^def test_' test_app.py         # 12
grep -rEn 'pytest\.skip|xfail' . --include='*.py' | wc -l   # 0
# to actually run: pip install flask flask-sqlalchemy && pytest test_app.py -v
```
