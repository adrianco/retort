# Evaluation: agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit_prompt=neutral_stack=q6 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit, prompt=neutral, stack=q6, framework=unknown
- **Status:** ok (`_meta.json` `succeeded: true`)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list — `rest-api-crud/REQUIREMENTS.json`); prompt instruction P1 followed
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — not re-run; `defect_rate=1.0` and `test_coverage=0.98` from `scores.json`
- **Lint:** pass — `code_quality=0.7888` from `scores.json` (no lint re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 4 low, 1 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` — IDs and order used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:37-69 create_book` — INSERT of all four columns, returns 201 with `lastrowid`; `test_app.py:21 test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:71-85 get_books` — `SELECT * FROM books`, 200; `test_app.py:43 test_get_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:74-78` — `request.args.get('author')` → `WHERE author LIKE ?`. Code-only evidence: no test exercises it (see finding `test-author-filter`) |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:87-98 get_book` — 200 / 404; `test_app.py:67 test_get_book_by_id`, `test_app.py:165 test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:100-138 update_book` — existence check then UPDATE, 200/404; `test_app.py:93 test_update_book`, `test_app.py:172 test_update_nonexistent_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:140-155 delete_book` — DELETE, 200/404; `test_app.py:125 test_delete_book` (asserts subsequent GET is 404), `test_app.py:186 test_delete_nonexistent_book` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.py:2,8,10-24` — `sqlite3` against file `books.db`, `CREATE TABLE IF NOT EXISTS books`; no in-memory dict anywhere |
| R8 | JSON responses with appropriate status codes | ✓ implemented | Every handler returns `jsonify(...)` with an explicit code: 201 `app.py:69`, 200 `app.py:35,85,98,138,155`, 400 `app.py:44,107`, 404 `app.py:96,121,149` |
| R9 | Input validation — title and author required | ✓ implemented | `app.py:43-44` (and `app.py:106-107` for PUT) reject missing title/author with 400; `test_app.py:151 test_create_book_missing_fields` asserts 400. Presence-only — see finding `validation-presence-only` |
| R10 | GET /health health check | ✓ implemented | `app.py:32-35 health_check` → `{"status":"healthy"}`, 200; `test_app.py:14 test_health_check` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup (`pip install -r requirements.txt`), run (`python app.py`), Testing, and curl examples per endpoint |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 10 `test_*` functions, 0 skips; `test_coverage=0.98` in `scores.json` confirms they executed |

### Prompt instructions (`prompts/neutral.md`, prompt=neutral)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | No methodology prescribed; include tests that demonstrate the implementation meets the requirements | ✓ implemented | `test_app.py` covers health, create, list, get-by-id, update, delete, validation-400 and three 404 paths. The one requirement with no demonstrating test is the `?author=` filter (R3) |

## Build & Test

Not re-run — per the skill, the stored mechanical scores stand in for the toolchain:

```text
cat scores.json
{"code_quality": 0.7888888888888889, "token_efficiency": 0.00372847989196899,
 "test_coverage": 0.98, "defect_rate": 1.0, "maintainability": 0.9935897435897436,
 "idiomatic": 0.75}
```

`test_coverage=0.98` (> 0) ⇒ the build succeeded and the suite executed; `defect_rate=1.0` ⇒
build + tests passed. Skip scan over the suite:

```text
grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   → 0
grep -c "^def test_" test_app.py                                 → 10
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 348 (`app.py` 158 + `test_app.py` 190) |
| Files (deliverables) | 4 (`app.py`, `test_app.py`, `requirements.txt`, `README.md`) |
| Files (all, excl. `__pycache__`/`.git`) | 18 (includes harness artifacts) |
| Dependencies | 1 declared (`flask`); pytest used but undeclared |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | not measured (build/test not re-run) |
| Agent API calls / total tokens | 47 / 1,475,132 (`.hermes_usage.json`) |

## Findings

All 7 are in `findings.jsonl`; nothing critical or high. Top 5 by severity:

1. `[medium]` **sec-debug-server** — `app.py:159` runs the Werkzeug dev server with `debug=True` bound to `0.0.0.0`, and README documents that as the run command.
2. `[medium]` **test-db-shared** — tests write to the same fixed `books.db` the service uses (`app.py:8`, `test_app.py:11`) with no teardown, so rows accumulate across runs.
3. `[low]` **dep-pytest-missing** — `requirements.txt` lists only `flask`, but `test_app.py:1` imports pytest and README's test command needs it.
4. `[low]` **test-author-filter** — the `?author=` filter (`app.py:74-78`) is implemented but untested.
5. `[low]` **init-db-main-only** — `init_db()` is called only under `if __name__ == '__main__'` (`app.py:157-158`), so a WSGI import leaves the table uncreated.

(Also: `[low]` validation-presence-only — empty-string title/author pass the check at `app.py:43`; `[info]` filter-substring-match — `LIKE '%…%'` rather than exact match at `app.py:78`.)

## Reproduce

```bash
cd experiments/adrianco/experiment-67-quant-6bit-knee/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-6bit_prompt=neutral_stack=q6/rep3

cat scores.json                       # stored mechanical scores (build/test/lint not re-run)
cat ../../../../REQUIREMENTS.json     # pinned 12-requirement checklist
cat ../../../../prompts/neutral.md    # prompt-factor instruction (P1)
grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
grep -c "^def test_" test_app.py
wc -l app.py test_app.py
```
