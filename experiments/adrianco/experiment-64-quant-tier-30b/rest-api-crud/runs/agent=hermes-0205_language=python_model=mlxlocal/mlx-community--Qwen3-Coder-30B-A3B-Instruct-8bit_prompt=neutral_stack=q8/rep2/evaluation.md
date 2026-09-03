# Evaluation: agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); prompt factor `neutral` → 1/1 followed
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — from `test_coverage=0.94`, `defect_rate=1.0`
- **Build:** pass — not re-run (import/collection succeeded, per `test_coverage=0.94 > 0` in `scores.json`)
- **Lint:** pass — `code_quality=0.789` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 9 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 7 low, 1 info)

Scores were read from `scores.json` rather than re-running the toolchain, per the
skill's Step 2:

```json
{"code_quality": 0.7888888888888889, "token_efficiency": 0.007585828404170986,
 "test_coverage": 0.94, "defect_rate": 1.0, "maintainability": 0.9711538461538461,
 "idiomatic": 0.7}
```

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 entries), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:37-76` `create_book` INSERTs all four columns; `test_app.py:21` `test_create_book` asserts 201 + echoed fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:79-105` `get_books` returns the full collection; `test_app.py:56` `test_get_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:81-88` — `request.args.get('author')` selects `WHERE author = ?`; `test_app.py:75` `test_get_books_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:108-126` `get_book` returns 404 when `fetchone()` is None; `test_app.py:95` and `test_app.py:171` `test_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:129-176` `update_book` — 404 check then UPDATE, returns re-selected row; `test_app.py:116` `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:178-200` `delete_book` — 404 check then DELETE; `test_app.py:150` `test_delete_book` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.py:2` `import sqlite3`, `app.py:8` `DATABASE = 'books.db'`, `app.py:10-24` `init_db` creates the `books` table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | every handler returns `jsonify(...), <code>` — 201 (`app.py:65`), 200, 400 (`app.py:44`), 404 (`app.py:120`), 500 (`app.py:76`) |
| R9 | Validation: title and author required | ✓ implemented | `app.py:43-45` and `app.py:133-135` reject falsy title/author with 400; `test_app.py:41` `test_create_book_missing_fields` asserts 400 |
| R10 | GET /health | ✓ implemented | `app.py:32-35` returns `{"status":"healthy"}`, 200; `test_app.py:14` `test_health_check` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:24-35` (pip install, `python app.py`, port 5001) and `README.md:37-41` (test command) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` defines 11 `test_*` functions; `test_coverage=0.94` confirms they executed |

### Prompt-factor instructions (`prompts/neutral.md`)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | No methodology prescribed; use your own judgement and include tests demonstrating the requirements are met | ✓ implemented | 11 tests in `test_app.py` cover every route plus the 400 and three 404 paths; no methodology was imposed, so nothing here is violated |

## Build & Test

Not re-run — the skill mandates reading the stored scores. Evidence from `scores.json`:

```text
test_coverage = 0.94   # > 0 ⇒ the suite built, imported and executed
defect_rate   = 1.0    # ⇒ build + tests succeeded
code_quality  = 0.789  # lint/quality
```

The agent's own transcript corroborates a green run (`_agent_stdout.log`):

```text
- ✅ app.py compiles successfully without syntax errors
- ✅ All 11 tests pass
```

Skip scan (Step 5) found none:

```text
$ grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
       0
```

So `effective_tests = 11 + 0 = 11`, skip ratio 0%.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 400 (`app.py` 203 + `test_app.py` 197) |
| Files (source + docs) | 4 (`app.py`, `test_app.py`, `README.md`, `requirements.txt`) |
| Dependencies | 1 (`Flask==2.3.3`) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | not re-run (scores read from `scores.json`) |
| Agent turns / API calls | 30 (`.hermes_usage.json`) |
| Total tokens | 819,950 (30,665 in / 6,181 out / 783,104 cache-read) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. `[medium] test-isolation-1` — tests share the real on-disk `books.db` with no teardown, so they are order-dependent and leak state (`test_app.py:5-12`, `app.py:8`).
2. `[low] test-weak-assert-1` — list/filter assertions use `len(data) >= 1`, which passes on residue from earlier tests (`test_app.py:73`, `test_app.py:92`).
3. `[low] err-handling-1` — bare `except Exception` collapses write errors into an opaque 500 and discards the exception (`app.py:75,174,198`).
4. `[low] conn-leak-1` — connections closed only on explicit paths; no context manager (`app.py:51,84,111,143,181`).
5. `[low] init-db-1` — `init_db()` runs only under `__main__`, so a WSGI deployment never creates the table (`app.py:202-204`).

Also: `put-semantics-1` (PUT nulls omitted `year`/`isbn`), `deps-1` (pytest missing from `requirements.txt`), `debug-1` (`debug=True` on `0.0.0.0`), and one `info` enhancement (11 tests vs. a 3-test minimum).

None of these block the spec: all 12 pinned requirements are met and the suite is green.

## Reproduce

```bash
cd experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep2

cat scores.json                                   # stored build/test/lint scores (Step 2)
cat ../../../../REQUIREMENTS.json                    # pinned 12-item checklist (Step 3)
cat ../../../../prompts/neutral.md                   # prompt-factor instructions
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
grep -c "^def test_" test_app.py                  # 11
wc -l app.py test_app.py README.md                # 203 / 197 / 47
```
