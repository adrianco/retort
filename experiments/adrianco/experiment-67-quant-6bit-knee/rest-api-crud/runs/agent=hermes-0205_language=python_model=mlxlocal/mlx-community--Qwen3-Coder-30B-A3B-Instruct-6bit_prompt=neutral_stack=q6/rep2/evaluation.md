# Evaluation: agent=hermes-0205 · python · mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit · prompt=neutral · stack=q6 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit, prompt=neutral, stack=q6, framework=unknown
- **Status:** ok — the run completed (`_meta.json: succeeded=true`, `retort.db` run 3 status=completed) and delivered a spec-complete implementation, **but the delivered test suite does not pass** (3 of 14 tests fail; see Findings).
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `../../../../REQUIREMENTS.json`; matches the stored `requirement_coverage=1.0`)
- **Prompt instructions:** P1 satisfied — `prompts/neutral.md` prescribes no methodology and asks for tests demonstrating the requirements; 14 tests are present covering every route.
- **Tests:** 11 passed / 3 failed / 0 skipped (14 effective)
- **Build:** pass (derived) — `test_coverage=0.92` from `scores.json` means pytest collected and executed, so `app.py` imports cleanly
- **Lint:** unavailable — `ruff` is not installed on this machine; `code_quality=0.79` from `scores.json` stands in
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 1 high, 3 medium, 3 low, 1 info)

Mechanical scores read from `scores.json` (not re-run): `test_coverage=0.92`,
`defect_rate=1.0`, `code_quality=0.7889`, `maintainability=0.9673`,
`idiomatic=0.62`, `token_efficiency=0.0034`. Cross-checked against `retort.db`
run id 3 (replicate 2, status=completed) — identical, plus
`requirement_coverage=1.0`, `_turns=59`, `_tokens=2290611`,
`_max_context_tokens=54198`, `_duration_seconds=576.87`, `_cost_usd=0.0`.

**Why the test failures are not visible in the stored scores.** For python,
`test_coverage` is the *line-coverage percentage* parsed from
`pytest --cov-report=term` (`src/retort/scoring/scorers/test_coverage.py:33`),
not a pass rate — 0.92 means 92 % of lines were executed, and failing
assertions still execute lines. `defect_rate` counts `ruff`/`py_compile`
findings (`src/retort/scoring/scorers/defect_rate.py:25-28`), not test
outcomes. So neither mechanical score reflects the 3 failures; they were found
by executing the suite on a copy (see Build & Test).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | `POST /books` creates a book (title, author, year, isbn) | ✓ implemented | `app.py:41 create_book` — INSERT at `app.py:62-65`, all four fields; `test_app.py:40 test_create_book_success` (passes) |
| R2 | `GET /books` lists all books | ✓ implemented | `app.py:83 get_books` — `SELECT * FROM books` at `app.py:93`, returns `200` JSON array at `app.py:109` |
| R3 | `GET /books` supports `?author=` filter | ✓ implemented | `app.py:85` reads `request.args.get('author')`; `app.py:91` `WHERE author LIKE ?` (substring match — see finding `filter-1`) |
| R4 | `GET /books/{id}` returns one book (404 if absent) | ✓ implemented | `app.py:112 get_book` — `404` at `app.py:122`, `200` at `app.py:124`; `test_app.py:176 test_get_book_by_id_not_found` (passes) |
| R5 | `PUT /books/{id}` updates a book | ✓ implemented | `app.py:133 update_book` — UPDATE at `app.py:163-167`, merges partial bodies against the existing row at `app.py:152-160`; `test_app.py:183` (passes) |
| R6 | `DELETE /books/{id}` deletes a book | ✓ implemented | `app.py:183 delete_book` — DELETE at `app.py:197`, `404` for a missing id at `app.py:194`; `test_app.py:257` (passes) |
| R7 | Data stored in SQLite | ✓ implemented | `import sqlite3` (`app.py:2`); `CREATE TABLE IF NOT EXISTS books` (`app.py:16-24`); file-backed at `app.py:8`, not in-memory |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify` on every path; `201` (`app.py:77`), `200`, `400` (`app.py:47,56,139,157`), `404` (`app.py:122,149,194`), `500` (`app.py:80,180,204`). Caveat: one uncaught path returns HTML `500` — finding `test-fail-2` |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:46` rejects a missing/absent body or field with `400`; `app.py:55` also rejects blank strings; `test_app.py:60 test_create_book_missing_fields` and `test_app.py:74 test_create_book_empty_fields` (both pass) |
| R10 | `GET /health` health check | ✓ implemented | `app.py:36 health_check` returns `{"status":"healthy"}, 200`; `test_app.py:33` (passes) |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — venv + `pip install -r requirements.txt` (lines 22-33), `python app.py` (line 36), curl examples (lines 50-89). Its test instruction is unrunnable as written — finding `dep-1` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 14 `def test_*` functions in `test_app.py`; suite executes (`test_coverage=0.92 > 0`). Satisfied as pinned, though 3 of the 14 fail |

No requirement is missing or partial. Enhancements beyond spec: empty-string
validation on both POST and PUT (`app.py:55`, `app.py:155`), `404`-before-write
guards on PUT/DELETE, a `DATABASE` env override (`app.py:8`, though it is read
too early to be useful in tests), and partial-update semantics on PUT.

## Build & Test

Per the skill, build/test/lint were **not** re-run for scoring — the stored
scores were used. The suite *was* executed once on a copy outside `run_dir`,
because the stored `test_coverage` is a coverage percentage and therefore
cannot distinguish a passing suite from a failing one:

```text
$ cp {app.py,test_app.py,requirements.txt} $SCRATCH/rep2copy/ && cd $SCRATCH/rep2copy
$ python3 -m pytest test_app.py -q
...
---------------------------- Captured stdout setup -----------------------------
Initializing database at: /private/tmp/.../rep2copy/books.db
Creating books table...
Database initialized successfully
=========================== short test summary info ============================
FAILED test_app.py::test_get_all_books_empty - AssertionError: assert [{'auth...
FAILED test_app.py::test_get_all_books_with_data - AssertionError: assert 2 == 1
FAILED test_app.py::test_get_books_by_author - AssertionError: assert 4 == 2
3 failed, 11 passed in 0.08s
```

The captured setup line is the diagnosis: the fixture's `tempfile.mkstemp()`
path is never used. `test_app.py:5` imports `app` first, which runs
`app.py:8`'s module-level `DB_FILE = os.path.abspath(os.environ.get('DATABASE',
'books.db'))`; the fixture's `os.environ['DATABASE'] = db_path` at
`test_app.py:15` comes too late. Every test therefore writes to one shared
`books.db` in the working directory, and the three tests that assert on
collection size see rows leaked from earlier tests.

Validation-crash probe (same copy, Flask test client):

```text
$ python3 -c "... c.post('/books', json={'title': 123, 'author': 'X'}) ..."
AttributeError: 'int' object has no attribute 'strip'   # app.py:55
non-string title -> 500 text/html; charset=utf-8
create -> 201
put non-string title -> 500                              # app.py:155
```

Lint: `ruff` is not on PATH here, so no fresh lint run was possible;
`code_quality=0.79` and `defect_rate=1.0` from `scores.json` are the recorded
signals.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 491 (`app.py` 207 + `test_app.py` 284) |
| Files (excluding harness/artifacts) | 7 (`app.py`, `test_app.py`, `requirements.txt`, `README.md`, `TASK.md`, `stack.json`, `scores.json`) |
| Source modules | 1 |
| Dependencies | 1 (`Flask==2.3.3`) |
| Tests total | 14 |
| Tests effective | 14 (11 pass, 3 fail, 0 skip) |
| Skip ratio | 0 % |
| Line coverage (stored) | 92 % |
| Turns | 59 |
| Total tokens | 2,290,611 |
| Peak context | 54,198 |
| Wall clock | 576.9 s |
| Cost | $0.00 (local MLX) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[high] `test-fail-1`** — 3 of 14 tests fail because `DB_FILE` is bound at import (`app.py:8`) so the temp-DB fixture (`test_app.py:11-15`) never takes effect and state leaks across tests.
2. **[medium] `test-fail-2`** — a non-string `title`/`author` raises `AttributeError` at `app.py:55` / `app.py:155` before the try block, returning a `500` HTML page instead of a `400` JSON validation error.
3. **[medium] `leak-1`** — `PUT /books/<id>` leaks its SQLite connection when that validation raises: the connection opens at `app.py:142` and both `conn.close()` calls (`app.py:156`, `app.py:169`) are skipped.
4. **[medium] `dep-1`** — `README.md:44-47` tells the user to run pytest after `pip install -r requirements.txt`, but `requirements.txt` pins only `Flask==2.3.3`.
5. **[low] `sec-1`** — the documented entrypoint runs the Werkzeug debugger on all interfaces (`app.py:208 app.run(debug=True, host='0.0.0.0')`).

Also: `lint-1` (low) unused `as e` in three `except` blocks; `lint-2` (low)
debug `print()`s in `init_db`; `filter-1` (info) `?author=` is a substring
`LIKE` match.

## Reproduce

```bash
run_dir="experiments/adrianco/experiment-67-quant-6bit-knee/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit_prompt=neutral_stack=q6/rep2"

# stored mechanical scores (authoritative; do not re-run the toolchain for these)
cat "$run_dir/scores.json"
sqlite3 -readonly experiments/adrianco/experiment-67-quant-6bit-knee/rest-api-crud/retort.db \
  "SELECT rr.metric_name, rr.value FROM run_results rr
     JOIN experiment_runs er ON er.id = rr.run_id
    WHERE er.replicate = 2 AND er.status = 'completed'
      AND json_extract(er.run_config_json,'\$.language') = 'python';"

# pinned requirement checklist
cat experiments/adrianco/experiment-67-quant-6bit-knee/rest-api-crud/REQUIREMENTS.json

# pass/fail ground truth (run on a COPY — run_dir is never modified)
work=$(mktemp -d)
cp "$run_dir"/{app.py,test_app.py,requirements.txt} "$work/"
( cd "$work" && python3 -m pytest test_app.py -q )        # -> 3 failed, 11 passed

# validation-crash probe
( cd "$work" && python3 -c "
from app import app, init_db
init_db()
c = app.test_client()
print('non-string title ->', c.post('/books', json={'title': 123, 'author': 'X'}).status_code)
" )                                                        # -> 500

# skipped-test count
grep -rE 'pytest\.skip|@pytest\.mark\.skip|xfail' "$run_dir" --include='*.py' | wc -l   # -> 0
```
