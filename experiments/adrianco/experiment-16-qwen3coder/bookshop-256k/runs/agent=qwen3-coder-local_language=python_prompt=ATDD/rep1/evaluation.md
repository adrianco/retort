# Evaluation: agent=qwen3-coder-local language=python prompt=ATDD · rep 1

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (Flask), prompt=ATDD
- **Status:** ok — all functional requirements met; the ATDD prompt directive was largely not followed and testing is weak
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing
- **Prompt (ATDD):** P1 partial — acceptance tests are not client-driven/atomic/independent and not written test-first
- **Tests:** 1 effective test (`test_api`) passed / 0 failed / 0 skipped — `test_coverage=0.07`
- **Build:** pass — `defect_rate=1.0` (build+test succeeded, from `scores.json`)
- **Lint:** pass — `code_quality=0.83` (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 2 low)

Scores read from `scores.json` (inline gate; no DB row matched, so DB not used):
`code_quality=0.833, test_coverage=0.07, defect_rate=1.0, maintainability=0.747, idiomatic=0.4, token_efficiency=0.0086`.
Per the skill, build/test/lint were **not** re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:36` create_book — inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:76` get_books returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:84-85` filters `WHERE author = ?` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:105` get_book, 404 at `app.py:114-115` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:125` update_book, 404 + validation |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:170` delete_book, 404 if absent |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:8-29` sqlite3, `books.db` on disk |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400 |
| R9 | Validation: title+author required | ✓ implemented | `app.py:42-43` (POST) and `app.py:131` (PUT) → 400 |
| R10 | GET /health | ✓ implemented | `app.py:31-34` returns `{'status':'healthy'}` |
| R11 | README setup + run | ✓ implemented | `README.md` setup, run, endpoint reference |
| R12 | ≥3 tests that run | ~ partial | only `simple_test.py:13` test_api(); `test_coverage=0.07` (>0 but <3 tests) |
| P1 | ATDD: client-driven, atomic, test-first | ~ partial | monolithic shared-state `test_api()`; `verify_implementation.py:68` always returns True (grep, not behavior); no red/green |

## Build & Test

Not re-run per skill (scores already computed). From `scores.json`:

```text
defect_rate = 1.0     # build + test executed successfully
test_coverage = 0.07  # tests ran but exercise ~7% of lines
```

Test inventory (grepped):

```text
def test_ functions found: 1  (simple_test.py:13 test_api)
skipped/xfail markers:      0
```

`test_api()` spawns `app.py` as a subprocess and drives all CRUD over HTTP in one
sequential flow (create→list→get→update→delete on a single shared book).
`verify_implementation.py` is a static grep checker, not a behavioral test.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, .py) | 664 total (app.py 191, app_clean.py 199, simple_test.py 110, verify_implementation.py 164) |
| Python files | 4 |
| Dependencies | 1 declared (Flask; README `pip install flask`, no requirements.txt) |
| Tests total | 1 (`test_api`) |
| Tests effective | 1 |
| Skip ratio | 0% |
| test_coverage | 0.07 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. **[high] P1** — ATDD prompt not followed: acceptance tests are not client-perspective/atomic/independent, not written test-first; `verify_implementation.py` always passes without exercising behavior.
2. **[medium] R12** — fewer than 3 tests (only `test_api`); `test_coverage=0.07`.
3. **[medium] test-noop-1** — `verify_implementation.py` masquerades as a test but never calls an endpoint (`verify_requirements()` returns True unconditionally).
4. **[low] dup-1** — `app_clean.py` is a dead near-duplicate of `app.py`.
5. **[low] sec-1** — `app.run(debug=True, host='0.0.0.0')` exposes the Werkzeug debugger on all interfaces.

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=python_prompt=ATDD/rep1
cat scores.json                                   # mechanical scores (not re-run)
grep -rEn "def test_" *.py                         # test inventory
grep -rEn "pytest\.skip|xfail|@pytest\.mark\.skip" *.py   # skip inventory
# functional check (optional): python app.py & then python simple_test.py
```
