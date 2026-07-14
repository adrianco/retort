# Evaluation: agent=hermes-local language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B, local), framework=unknown (Flask), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — `test_coverage=0.93` from scores.json
- **Build:** pass — tests import & run (defect_rate=1.0)
- **Lint:** pass — `code_quality=0.79` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:59 create_book` — INSERTs title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:93 list_books` — SELECT * returns list |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:100-104` — `WHERE author LIKE '%..%'`; test at `test_app.py:107` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:113 get_book` — 404 at `app.py:120` when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:128 update_book` — UPDATE, 404/400 handling |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:172 delete_book` — DELETE, 404 handling |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:26 init_db`, `sqlite3.connect`, WAL mode |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400/500 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:72-76` (create), `app.py:143-158` (update) → 400 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:53 health_check` → `{status: healthy}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 15 tests, all pass |

**Prompt factor (neutral):** the neutral prompt prescribes no methodology and only
asks for tests demonstrating the requirements — satisfied by the 15-test suite.
No additional checkable `P*` instructions.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate scores):

```text
scores.json: test_coverage=0.93, defect_rate=1.0, code_quality=0.79,
             maintainability=1.0, idiomatic=0.76, token_efficiency=0.006
```

```text
Agent stdout: "Test results: 15/15 passed in 0.07s"
test_coverage=0.93 ⇒ build + tests executed and passed (0.93 line coverage).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 361 (app.py 196 + test_app.py 165) |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | flask, pytest (undeclared — no manifest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | ~0.07s (test suite, per agent log) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Handlers return raw exception text (`str(e)`) to clients — `app.py:89-90` et al.
2. [low] No dependency manifest (requirements.txt / pyproject.toml) — pytest undeclared.
3. [info] year/isbn accepted without type/format validation (beyond spec).

No critical, high, or medium findings — a clean, spec-complete run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep2
cat scores.json                 # mechanical scores (build/test/lint), do not re-run
grep -cE "def test_" test_app.py # 15
grep -rE "pytest\.skip|xfail" test_app.py | wc -l  # 0 skips
# to re-run tests independently: python -m pytest test_app.py -v
```
