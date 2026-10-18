# Evaluation: rest-api-crud · python · ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ · tcap · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0222, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, prompt=neutral, stack=tcap
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — `test_coverage=0.97`, `defect_rate=1.0` (from `scores.json`; not re-run)
- **Lint:** pass — `code_quality=0.62`, `idiomatic=0.60`, `maintainability=1.0` (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:110 create_book`, INSERT at `app.py:121`; `test_create_book_returns_201_and_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:129 list_books`; `test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:133-136` WHERE author=?; `test_list_books_author_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:142 get_book`, 404 at `app.py:148`; `test_get_book`, `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:151 update_book` (partial updates); `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:176 delete_book` returns 204; `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:37 init_db` CREATE TABLE, `sqlite3.connect` throughout |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400/204 across handlers |
| R9 | Validation: title and author required | ✓ implemented | `app.py:76-84 parse_book_payload`; `test_create_book_requires_title/author` |
| R10 | GET /health health-check | ✓ implemented | `app.py:106 health` → `{"status":"ok"}` 200; `test_health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` setup/run/endpoints/examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 17 tests in `test_app.py`; `test_coverage=0.97` |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate; run not yet in `retort.db`):

```text
scores.json: test_coverage=0.97  defect_rate=1.0  maintainability=1.0
             code_quality=0.622  idiomatic=0.60  token_efficiency=0.0078
```

```text
Agent self-report (_agent_stdout.log): 17/17 pass on system Python 3.11 and venv 3.13.
`hermes verify --json` returned ok:true. Default port 5000 collides with macOS
ControlCenter (AirPlay) on this host — app port is configurable via PORT; a smoke
test on 5001 exercised every endpoint. Host conflict, not an app defect.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + test_app.py) | 337 |
| Files (excl. caches) | 15 (4 primary: app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (no critical/high/medium):

1. [low] `init_db()` only called under `__main__`, not in `create_app()` — a WSGI deploy of the module-level `app` would not auto-create the table (`app.py:189` vs `app.py:192`).
2. [info] Validation exceeds spec — non-JSON body, empty strings, non-int year, empty isbn all rejected.
3. [info] 17 tests vs the 3 required.

## Reproduce

```bash
cd "experiments/adrianco/experiment-88-thinkingcap-screen/rest-api-crud/runs/agent=hermes-0222_language=python_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap/rep1"
cat scores.json                                   # stored mechanical scores (not re-run)
grep -cE "^def test_" test_app.py                 # 17 tests
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
python -m pytest test_app.py -v                   # optional: re-run tests
```
