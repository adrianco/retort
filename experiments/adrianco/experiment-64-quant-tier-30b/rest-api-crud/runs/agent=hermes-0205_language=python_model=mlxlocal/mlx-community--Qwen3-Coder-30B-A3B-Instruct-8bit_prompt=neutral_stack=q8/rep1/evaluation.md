# Evaluation: agent=hermes-0205 · python · Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 1

> **Second-opinion pass.** This re-checks the prior evaluation (`_judge/attempt-002.stdout.log`),
> which scored `requirement_coverage = 0.9167` by marking **R9 partial**. That deduction is
> **overturned** — see [Re-check of the prior evaluation](#re-check-of-the-prior-evaluation).

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8, framework=unknown (Flask, chosen by the agent)
- **Status:** ok — all 12 pinned requirements implemented, but the shipped test suite does not pass clean
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator fixed at 12)
- **Tests:** 7 passed / 2 failed / 0 skipped (9 effective)
- **Build:** pass — `defect_rate=1.0` from `scores.json` (py_compile/ruff clean enough to score 1.0); the app imports and serves
- **Lint:** `code_quality=0.7889` from `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 3 low)

## Re-check of the prior evaluation

The prior pass claimed one requirement was not fully met:

**R9 — "Input validation: title and author are required" — claimed `partial`.**
**Overturned: R9 is `implemented`.** The pinned `how_to_verify` for R9 is
*"Creating without title/author is rejected (400)."* The code does exactly that at
`app.py:44-45` (`if not data or 'title' not in data or 'author' not in data: → 400`) and
again on PUT at `app.py:136-137`. Probed against a clean database:

```text
missing author -> 400
missing title  -> 400
empty strings  -> 201
health         -> 200 {'status': 'healthy'}
```

`test_app.py:62-75` (`test_create_book_missing_fields`) exercises this path and passes.
The prior pass deducted for the third line — empty-string title/author is accepted — which
is a real weakness but is **beyond** R9's stated criterion. Per the skill's rule that the
pinned checklist is the spec and evaluators must not add to it, that belongs in
`findings.jsonl` as a low-severity item (`val-1`), not as a requirement deduction.
Re-scored: **12/12 = 1.0**.

The prior pass's other central claim — that **2 of 9 tests fail** despite
`test_coverage=0.91` — is **confirmed**, independently reproduced below. It stays a `high`
finding; it just isn't a requirement deduction, because R12's criterion is
*">= 3 tests exist and run (test_coverage > 0)"* and 9 tests exist and run.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 entries, verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:38-78` `create_book` — INSERT of all four columns, returns 201 with the created row; `test_app.py:42` passes |
| R2 | GET /books lists all books | ✓ implemented | `app.py:80-107` `get_books` — `SELECT * FROM books`, returns a JSON list, 200 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:83,88-89` — `request.args.get('author')` → `WHERE author LIKE ?`; verified live: `?author=Orwell` returns only Orwell rows |
| R4 | GET /books/{id} returns one book | ✓ implemented | `app.py:109-128` `get_book` — 200 with the row, `app.py:119-120` returns 404 when absent; `test_app.py:217` passes |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:130-177` `update_book` — 404 if absent (`app.py:151`), UPDATE then returns the updated row; `test_app.py:160` passes |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:179-201` `delete_book` — 404 if absent, DELETE + 200; `test_app.py:192` passes (including the follow-up 404) |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:2,10` `sqlite3.connect(DATABASE)`; `app.py:14-28` `init_db` creates the `books` table on disk. Confirmed: a `books.db` file appears in the CWD when the app or the suite runs |
| R8 | JSON responses with appropriate status codes | ✓ implemented | Every route returns `jsonify(...)` with an explicit code — 201 (`app.py:74`), 200, 400 (`app.py:45`), 404 (`app.py:120`), 500 (`app.py:78`) |
| R9 | Validation: title and author required | ✓ implemented | `app.py:44-45` and `app.py:136-137` reject missing title/author with 400; probe returns 400 for both cases. (Empty strings accepted → low finding `val-1`, outside R9's criterion) |
| R10 | GET /health endpoint | ✓ implemented | `app.py:33-36` `health_check` → `{'status': 'healthy'}`, 200; probe confirms; `test_app.py:35` passes |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:23-35` (`pip install -r requirements.txt`, `python app.py`, port 5000), plus endpoint table, curl examples and a test-run section at `README.md:73-78` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 test functions in `test_app.py`; they execute (`test_coverage=0.91` > 0). Two of them fail — tracked as finding `test-fail-1`, not as a requirement gap |

No `P*` prompt requirements: `stack.json` has `prompt=neutral`, and no `prompts/neutral.md`
adds checkable instructions beyond TASK.md.

**Beyond spec (not deductions):** 404 handling on GET/PUT/DELETE, substring (`LIKE`) author
matching rather than exact, validation also enforced on PUT, and 6 tests beyond the required 3.

## Build & Test

Mechanical scores read from `scores.json` (not re-run):

```text
{"code_quality": 0.7888888888888889, "token_efficiency": 0.0032493890946047994,
 "test_coverage": 0.91, "defect_rate": 1.0, "maintainability": 0.9698717948717949,
 "idiomatic": 0.55}
```

`test_coverage=0.91` here is a **coverage percentage**, not a pass rate, so it does not
answer "do the tests pass". That question had to be settled directly — the one place this
evaluation departed from "read the stored scores". An untouched copy of `app.py` +
`test_app.py` in a scratch directory with no pre-existing `books.db`:

```text
$ python3 -m pytest test_app.py -v
FAILED test_app.py::test_get_books - AssertionError: assert 2 == 1
FAILED test_app.py::test_get_books_by_author - AssertionError: assert 4 == 2
2 failed, 7 passed in 0.06s
```

This is deterministic from a clean checkout, not stale-state flakiness: `test_app.py:17-22`
builds a tempfile database and sets `app.config['DATABASE']`, but `app.py:6` uses a
module-level `DATABASE = 'books.db'` that nothing reads, so the override is dead and all
nine tests accumulate rows in one shared file. By the time `test_get_books` runs,
`test_create_book` has already inserted a row, so `len(data) == 1` fails.

The **endpoints themselves are correct** — the `?author=` filter still returns only
matching rows against the polluted database. The defect is confined to test isolation.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 426 (`app.py` 205 + `test_app.py` 221) |
| Files (excl. `__pycache__`, `.git`) | 26 (4 hand-written: `app.py`, `test_app.py`, `README.md`, `requirements.txt`) |
| Dependencies | 1 (`Flask==2.3.3`) |
| Tests total | 9 |
| Tests effective | 9 |
| Tests passing | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; `defect_rate=1.0` from `scores.json`) |

## Findings

Full list in [`findings.jsonl`](findings.jsonl):

1. **[high]** `test-fail-1` — 2 of 9 tests fail on a clean checkout; the fixture's tempfile-DB isolation at `test_app.py:17-22` is dead code because `app.py:6` hardcodes `DATABASE='books.db'`.
2. **[medium]** `sec-1` — `app.py:206` runs with `debug=True, host='0.0.0.0'`, exposing the Werkzeug debugger (arbitrary code execution) on all interfaces.
3. **[low]** `val-1` — validation is key-presence only; `{"title":"","author":""}` → 201. Meets R9's pinned criterion, but weaker than intended.
4. **[low]** `lint-1` — `app.py:76,175,199` bind `except Exception as e` and never use `e`; the 500 discards the cause with no logging.
5. **[low]** `db-1` — `books.db` is created in the process CWD with no configuration hook and no mention in `README.md`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep1"

# pinned checklist (fixed denominator = 12)
cat ../../../../REQUIREMENTS.json

# stored mechanical scores — do not re-run build/lint
cat scores.json

# the one thing scores.json cannot answer: does the suite pass?
S=$(mktemp -d); cp app.py test_app.py requirements.txt "$S"/
(cd "$S" && python3 -m pytest test_app.py -v)   # 2 failed, 7 passed

# R9 probe
(cd "$S" && rm -f books.db && python3 -c "
from app import app, init_db
init_db(); c = app.test_client()
print('missing author ->', c.post('/books', json={'title':'x'}).status_code)
print('missing title  ->', c.post('/books', json={'author':'y'}).status_code)
print('empty strings  ->', c.post('/books', json={'title':'','author':''}).status_code)
print('health         ->', c.get('/health').status_code, c.get('/health').get_json())")

# no skipped/xfail tests
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
```
