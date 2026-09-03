# Evaluation: agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit_prompt=neutral_stack=q6 · rep 5

## Summary

- **Factors:** language=python, model=`mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit`, agent=hermes-0205, prompt=neutral, stack=q6, framework=unknown
- **Status:** ok — `_meta.json` `succeeded: true`, no `-failed` suffix
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned checklist from `../../../../REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — `test_coverage=0.91`, `defect_rate=1.0` from `scores.json` (build+tests ran and succeeded); not re-run for scoring
- **Lint:** `code_quality=0.79` from `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 13 items in `findings.jsonl` (0 critical, 0 high, 4 medium, 7 low, 2 info)

A complete, working single-file Flask + raw-`sqlite3` CRUD service. Every route the spec asks
for exists, validation returns 400, missing ids return 404, the README documents setup and
usage, and 9 tests cover all six endpoints with no skips. Nothing in the run is a conformance
failure. The defects are all quality-level: the test suite's database override silently does
nothing (so tests run against the production `books.db` and leak rows), the README points at
the wrong port, `requirements.txt` names a library the code never uses while omitting `pytest`,
and the documented run command starts a debug server on `0.0.0.0`.

## Requirements

Pinned checklist — IDs and text verbatim from `REQUIREMENTS.json`; denominator fixed at 12.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:37-69` — INSERT of all four columns, returns 201; `test_app.py:23 test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:71-81 get_books` — `SELECT * FROM books`; `test_app.py:44 test_get_books` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `app.py:74-78` — `request.args.get('author')` → `WHERE author LIKE ?`; `test_app.py:171 test_filter_books_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:85-95 get_book` — 404 branch at `app.py:93`; `test_app.py:68 test_get_book_by_id`, `test_app.py:164 test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:97-134 update_book` — UPDATE of all four columns, 404 if absent; `test_app.py:92 test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:136-153 delete_book` — DELETE + 404 branch; `test_app.py:125 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:2 import sqlite3`, `app.py:8 DATABASE = 'books.db'`, `app.py:10-24 init_db` CREATE TABLE — on-disk SQLite, not in-memory state |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify` on every route; 201 at `app.py:66`, 400 at `app.py:44`, 404 at `app.py:93`, 500 at `app.py:69`. (One gap: a malformed JSON *body* yields Flask's HTML 400 page — see `malformed-json-html`.) |
| R9 | Input validation — title and author required | ✓ implemented | `app.py:43` rejects a body missing either key with 400; `test_app.py:148 test_create_book_missing_fields` asserts 400. (Presence-only — blank strings pass; see `validation-presence-only`.) |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:32-35 health_check` → `{'status': 'healthy'}`, 200; `test_app.py:16 test_health_check` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:24-41` — install, run, test sections, plus curl examples. (Port is wrong — see `doc-port-mismatch`.) |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 `test_*` functions in `test_app.py`; `test_coverage=0.91` in `scores.json` confirms they executed |

**Prompt-factor instructions.** `stack.json` has `prompt: neutral`; `prompts/neutral.md` prescribes
no methodology and asks only for "tests that demonstrate the implementation meets the requirements".

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Include tests demonstrating the implementation meets the requirements | ✓ implemented | 9 tests exercise all six routes plus the 400 and 404 paths (`test_app.py:16-201`); no methodology was imposed and none was claimed |

## Build & Test

Mechanical scores were read, not recomputed, per the skill's Step 2:

```text
cat scores.json
{"code_quality": 0.7888888888888889, "token_efficiency": 0.00679431141983939,
 "test_coverage": 0.91, "defect_rate": 1.0, "maintainability": 0.9948717948717949,
 "idiomatic": 0.38}
```

`test_coverage=0.91` (> 0) and `defect_rate=1.0` ⇒ the build/import succeeded and the suite ran
and passed. The suite was additionally re-run **on a temp copy outside `run_dir`**, not to
re-score but to test the isolation hypothesis behind the `test-db-shared` finding:

```text
$ python3 -m pytest test_app.py -q      # run 1, clean directory
.........                                                                [100%]
9 passed in 0.05s
$ sqlite3 books.db 'select count(*) from books'   →  6      # test_books.db never created
$ python3 -m pytest test_app.py -q      # run 2, same directory
9 passed in 0.04s
$ sqlite3 books.db 'select count(*) from books'   →  12     # rows accumulate
```

Skip scan — zero:

```text
$ grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `app.py`) | 156 |
| Lines of code (source + tests) | 357 |
| Files (source/docs, excl. harness + artifacts) | 4 (`app.py`, `test_app.py`, `requirements.txt`, `README.md`) |
| Dependencies declared | 2 (`Flask==2.3.3`, `Flask-SQLAlchemy==3.0.5` — the latter unused; `pytest` undeclared) |
| HTTP routes | 6 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Agent API calls / total tokens | 29 / 815,388 (`.hermes_usage.json`) |
| Stored scores | test_coverage 0.91 · code_quality 0.79 · defect_rate 1.0 · maintainability 0.99 · idiomatic 0.38 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. `[medium] test-db-shared` — the fixture's `app.config['DATABASE']` override is never read (`app.py:8` module-level constant), so tests write to the real `books.db` and leak 6 rows per run.
2. `[medium] test-assertions-tolerant` — `>=` assertions and a hard-coded `GET /books/999` hide that leakage, and will eventually flip that test to a false failure.
3. `[medium] sec-debug-server` — `app.py:157 app.run(debug=True, host='0.0.0.0', port=5001)` is what `README.md:32` tells the user to run.
4. `[medium] dep-pytest-missing` — the README's test command cannot be followed from a clean venv; `pytest` is not in `requirements.txt`.
5. `[low] dep-unused-sqlalchemy` — `Flask-SQLAlchemy` is pinned but never imported (nor is `os`, imported at `app.py:3`).

## Reproduce

```bash
cd experiments/adrianco/experiment-67-quant-6bit-knee/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit_prompt=neutral_stack=q6/rep5

cat scores.json _meta.json _effective_stack.json          # stored mechanical scores + factors
cat ../../../../REQUIREMENTS.json                          # pinned 12-requirement checklist
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
grep -c "^def test_" test_app.py

# isolation probe — on a COPY, never in run_dir
cp app.py test_app.py "$TMPDIR/rep5copy/" && cd "$TMPDIR/rep5copy"
python3 -m pytest test_app.py -q
python3 -c "import sqlite3;print(sqlite3.connect('books.db').execute('select count(*) from books').fetchone())"
python3 -m pytest test_app.py -q && python3 -c "import sqlite3;print(sqlite3.connect('books.db').execute('select count(*) from books').fetchone())"
```
