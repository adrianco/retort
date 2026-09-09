# Evaluation: agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (chosen by the agent: Flask)
- **Status:** ok — repair pass (`_second_try=1.0`); the first attempt for this cell is archived at `../rep3-failed/`
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`); prompt instruction P1 satisfied
- **Tests:** 10 tests defined, all executing, 0 skipped (10 effective) — `defect_rate=1.0`, `test_coverage=0.99` from `scores.json`
- **Build:** pass — not re-run; `defect_rate=1.0` in `scores.json` ⇒ build + tests succeeded. Wall clock for the run: 110.1s (`_duration_seconds`, retort.db)
- **Lint:** pass with warnings — `code_quality=0.7889` from `scores.json`; 9 over-long lines + 2 function-local imports identified statically
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 6 items in [`findings.jsonl`](findings.jsonl) (0 critical, 0 high, 0 medium, 3 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 entries), used verbatim so
`requirement_coverage` shares a denominator with every other run of
`rest-api-crud`.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:92 create_book` → INSERT at `app.py:96`; all four fields bound from `payload()` (`app.py:73-74`); returns 201 + Location (`app.py:98`); `test_app.py:21 test_crud` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:101 list_books` → `SELECT * FROM books ORDER BY id` (`app.py:104`); `test_app.py:27` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:102-106` reads `request.args.get("author")` and filters with a bound parameter; `test_app.py:35 test_filter_exact_and_sql_safe` asserts 1 match for `Alice` |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `app.py:110 get_book` → `app.py:76 book_by_id` raises `NotFound`; `test_app.py:59` checks `/books/999` → 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:114 update_book` → UPDATE at `app.py:119`, re-reads and returns the row; `test_app.py:83 test_updated_fields_persist_and_delete_persists` asserts every field changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:123 delete_book` → DELETE at `app.py:127`, returns 204; `test_app.py:31-33` confirms the row is gone from both the item and list routes |
| R7 | Data stored in SQLite | ✓ implemented | `import sqlite3` (`app.py:3`), schema at `app.py:40-46`, file-backed default `books.sqlite3` (`app.py:13`); `test_app.py:67 test_persistence` proves a second `create_app()` reads the same row |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 (`app.py:98`), 200 (`app.py:107`, `:111`, `:120`), 204 (`app.py:128`), 400 (`app.py:60-72`), 404 (`app.py:80,83`); `app.py:49-54` re-renders every `HTTPException` — 404/405/415 included — as `{"error": …}`; `test_app.py:53,59` assert JSON bodies on 400/404/405/415 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:64-66` rejects non-string or blank `title`/`author` with 400, backed by table CHECK constraints (`app.py:42-43`); `test_app.py:42 test_invalid_input` covers 13 rejection cases including `{"title":"x"}` and `{"author":"x"}` |
| R10 | GET /health | ✓ implemented | `app.py:86-89` returns `{"status":"ok"}` after a `SELECT 1` connectivity probe; `test_app.py:101 test_health_and_optional_fields` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — venv + `pip install -r requirements.txt` + `python app.py`, the `flask --app` alternative, `BOOKS_DATABASE` override, a full route table, and curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` defines 10 `test_*` methods on `BooksAPITest`; `test_coverage=0.99` ⇒ they executed |

### Prompt-factor instructions (`prompts/neutral.md`)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | No methodology prescribed; include tests demonstrating the implementation meets the requirements | ✓ implemented | 10 tests exercise every route and both error classes; `test_app.py:67` and `:83` verify persistence across app instances rather than only in-process state |

No requirement was scored `partial`, `missing`, or `cannot-verify`.

## Build & Test

Not re-run — retort's scorers already executed the toolchain for this run and
stored the results.

```text
$ cat scores.json
{"code_quality": 0.7888888888888889, "token_efficiency": 0.010145040094751761,
 "test_coverage": 0.99, "defect_rate": 1.0, "maintainability": 1.0, "idiomatic": 0.85}
```

`defect_rate=1.0` ⇒ build + tests succeeded; `test_coverage=0.99` ⇒ tests
executed. Cross-checked against the experiment database, which agrees exactly:

```text
$ sqlite3 -readonly ../../../retort.db "SELECT metric_name, value FROM run_results WHERE run_id = (…rep 3, status='completed'…)"
code_quality|0.788888888888889
test_coverage|0.99
defect_rate|1.0
maintainability|1.0
idiomatic|0.85
_duration_seconds|110.060712583363
_tokens|412024.0
_second_try|1.0
_cost_usd|0.798448
_agent_steps|18.0
```

The agent's own last recorded test run in `_agent_stdout.log` (`Ran 8 tests in
0.032s … OK`) predates the final two tests it went on to add; the scorer's later
run over all 10 is what the metrics above reflect.

### Skipped / disabled tests

```text
$ grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail|unittest\.skip|@skip" --include="*.py" . | wc -l
0
```

No skips, no `xfail`, no disabled tests. `effective_tests = 10`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 247 (`app.py` 134 + `test_app.py` 113) |
| Files (excl. build artifacts) | 15 total in the archive; 6 authored (`app.py`, `test_app.py`, `README.md`, `pyproject.toml`, `requirements.txt`, `.gitignore`) |
| Dependencies | 1 runtime (`Flask>=2.3.3,<4`), 1 test extra (`pytest>=7,<9`) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | not measured separately; run wall clock 110.1s |
| Agent steps / tokens / cost | 18 steps, 412,024 tokens, $0.798 |

## Findings

All 6 findings, by severity (0 critical, 0 high, 0 medium):

1. `[low] lint-1` — 9 source lines exceed 100 columns and `BadRequest`/`NotFound` are imported inside function bodies (`app.py:57`, `app.py:77`) while `HTTPException` is imported at `app.py:8`.
2. `[low] robust-1` — the JSON error handler is registered for `HTTPException` only (`app.py:49`), so an unexpected `sqlite3.OperationalError` from `health()` (`app.py:88`) escapes as an HTML 500; `/health` has no unhealthy branch.
3. `[low] sqlite-1` — no `busy_timeout` on the per-request connections (`app.py:28`), so concurrent writers on the threaded dev server can hit `database is locked` with no retry.
4. `[info] R3-note` — the `?author=` filter is exact and case-sensitive (`app.py:106`); documented in README and pinned by `test_app.py:39-40`. Not a deduction — TASK.md specifies no matching semantics — recorded so cross-run comparison can tell the two styles apart.
5. `[info] enh-1` — above-spec work: universal JSON errors, unknown-field rejection, bool-excluded/int64-range `year` validation, `Location` on create, and a `:memory:` mode rewritten to a keeper-pinned shared-cache URI DB.
6. `[info] repair-1` — this cell is a repair pass; the failed first attempt is at `../rep3-failed/`.

Note on taxonomy: `robust-1` and `sqlite-1` are robustness defects rather than
above-spec suggestions, but `evaluate-run`'s allowed `kind` vocabulary has no
better fit and classifying them as `requirement_partial` would wrongly reduce
R8's coverage — every specified path does return JSON with the right status.

## Reproduce

```bash
cd experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep3

cat stack.json _meta.json scores.json
cat ../../../REQUIREMENTS.json
cat ../../../prompts/neutral.md

sqlite3 -readonly ../../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id = (SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='python'
      AND json_extract(er.run_config_json,'\$.model')='gpt-6-astra'
      AND er.replicate=3 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"

grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail|unittest\.skip|@skip" --include="*.py" . | wc -l
grep -cE "^\s+def test_" test_app.py
awk 'length>100 {printf "%s:%d len=%d\n", FILENAME, FNR, length}' app.py test_app.py
wc -l app.py test_app.py
```

Build, tests and lint were deliberately NOT re-run — the stored scores stand in
for them, per the `evaluate-run` contract.
