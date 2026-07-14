# Evaluation: agent=qwen3-coder-local language=python prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=Flask (inferred), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); tests import & run
- **Lint:** pass — `code_quality=0.7888` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low)

Mechanical scores read from `scores.json` (inline gate; no rerun):
`test_coverage=0.90`, `defect_rate=1.0`, `code_quality=0.789`,
`maintainability=0.971`, `idiomatic=0.68`, `token_efficiency=0.0061`.

The neutral prompt (`prompts/neutral.md`) prescribes no methodology and adds no
discrete checkable instructions, so there are no `P*` requirements — `REQUIREMENTS.json`
is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:55 create_book` INSERTs 4 fields, 201; test `test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:96 get_books`; test `test_get_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:105-106` WHERE author=?; test `test_get_books_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:130 get_book`, 404 at :142; tests `test_get_single_book`, `test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:156 update_book`; tests `test_update_book`, `test_update_nonexistent_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:205 delete_book`; tests `test_delete_book`, `test_delete_nonexistent_book` |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:1` `sqlite3`, `init_db()` creates `books` table in `books.db` |
| R8 | JSON + proper status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400/500 throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:36 validate_book_data` → 400; test `test_create_book_missing_fields` |
| R10 | GET /health | ✓ implemented | `app.py:49 health_check` → `{status: healthy}` 200; test `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` present (setup, run, curl examples) — see doc mismatches below |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 11 tests in `test_app.py`; `test_coverage=0.90 > 0`, `defect_rate=1.0` |

## Build & Test

Not re-run — mechanical scores were read from `scores.json` (inline eval gate),
per the skill's do-not-rerun rule.

```text
scores.json: test_coverage=0.90  defect_rate=1.0  code_quality=0.7889
             maintainability=0.9709  idiomatic=0.68
```

```text
app.log confirms live exercise of every route:
GET /health 200 · POST /books 201 · GET /books 200 · GET /books/1 200
PUT /books/1 200 · DELETE /books/1 200 · GET /books/1 404 · GET /books?author=... 200
No test skips (grep for unittest.skip/pytest.skip/xfail = 0).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 231 (app.py) |
| Lines of code (tests) | 247 (test_app.py) |
| Files (source + test + README) | 3 |
| Dependencies | 1 real (Flask); README also lists unused aiosqlite; no requirements.txt |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage | 90% (`test_coverage=0.90`) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] Flask dev server launched with `debug=True` bound to `0.0.0.0` — Werkzeug debugger active (RCE risk); `app.py:232`.
2. [low] README port/base URL (5000) does not match code (5001); `README.md` vs `app.py:232`.
3. [low] README lists unused `aiosqlite` dependency; code uses stdlib `sqlite3`; no `requirements.txt`.
4. [low] Missing/invalid JSON body on POST/PUT yields 500 instead of 400; `app.py:58`.

No critical or high findings: all 12 requirements are implemented, tests pass,
and no tests are skipped.

## Reproduce

```bash
cd "experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=python_prompt=neutral/rep3"
cat scores.json                       # mechanical scores (no rerun)
grep -cE "def test_" test_app.py      # 11 tests
grep -rE "unittest.skip|pytest.skip|xfail" *.py | wc -l   # 0 skips
# optional live rerun (not required — scores already stored):
python -m pytest test_app.py -q
```
