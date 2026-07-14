# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s7 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask, inferred), prompt=none, stack=s7
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.97, defect_rate=1.0)
- **Lint:** pass — code_quality=0.7889, idiomatic=0.77, maintainability=0.9974 (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:68 create_book` — INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:104 list_books` — SELECT * + 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:110-114` — `WHERE author LIKE ?` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:132 get_book` — 200; 404 at `app.py:139` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:150 update_book` — UPDATE + 200 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:190 delete_book` — DELETE + 200 |
| R7 | Data in SQLite | ✓ implemented | `app.py:11,27` — `sqlite3.connect`, `CREATE TABLE books` |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout |
| R9 | Validate title & author required | ✓ implemented | `app.py:80-84` — 400 when missing/blank |
| R10 | GET /health | ✓ implemented | `app.py:63 health_check` — `{"status":"healthy"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, usage, testing sections |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 18 tests; test_coverage=0.97 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2).

```text
scores.json: test_coverage=0.97  defect_rate=1.0  maintainability=0.9974
             code_quality=0.7889  idiomatic=0.77  token_efficiency=0.0078
```

```text
Agent stdout log reports: "Test results: 18/18 passed"
grep "def test_" test_app.py = 18   |   skip/xfail markers = 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 439 (app.py 208, test_app.py 231) |
| Files | 12 (incl. .db/.coverage/logs; 4 source+doc: app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `create_app` mutates module-global `DATABASE` for the test-DB override — not parallel-safe (`app.py:43-47`)
2. [info] POST /books silently ignores unknown JSON fields (`app.py:75-78`)
3. [info] Test suite exceeds the 3-test minimum with strong edge-case coverage (18 tests, 6 classes)

No critical/high/medium findings. This run cleanly satisfies the full spec.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s7/rep3
cat scores.json                               # mechanical scores (build/test/lint)
grep -cE "def test_" test_app.py              # 18
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0
# optional re-run: pip install -r requirements.txt && pytest test_app.py -v
```
