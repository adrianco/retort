# Evaluation: effort=medium language=python model=claude-sonnet-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.95, defect_rate=1.0; no build step for pure-stdlib Python)
- **Lint:** pass — code_quality=0.79 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Denominator fixed at 12 by the task's pinned `REQUIREMENTS.json`.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:63-71` INSERT + 201; `test_app.py:39 test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `app.py:77-79`; `test_app.py:53 test_list_and_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:74-76` `WHERE author=?`; `test_app.py:57` asserts filtered result |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:91-92`, 404 at `app.py:89-90`; `test_app.py:69 test_not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:97-100`; `test_app.py:61 test_update_delete` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:93-96` returns 204; `test_app.py:65` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15-25` `Store` creates `books` table via `sqlite3` |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:9-11` STATUS map, `app.py:118-123` json.dumps + Content-Type |
| R9 | Validation: title & author required | ✓ implemented | `app.py:32-48 validate()`; `test_app.py:45 test_validation` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:59-60`; `test_app.py:35 test_health` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` documents Run/Test/Endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 tests in `test_app.py`; test_coverage=0.95 |

## Build & Test

No build/test re-run — stored scores used per skill (test_coverage=0.95 ⇒ build+all tests passed).

```text
scores.json:
  test_coverage   = 0.95   (build + tests passed; only __main__ launch shim uncovered)
  defect_rate     = 1.0    (build+test succeeded)
  code_quality    = 0.7889
  maintainability = 0.9587
  idiomatic       = 0.45
  token_efficiency= 0.0405
```

```text
tests: 6 collected, 6 passed, 0 skipped (grep pytest.skip/xfail = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 215 (app.py 142 + test_app.py 73) |
| Files (source) | 2 (app.py, test_app.py) + README.md |
| Dependencies | 0 runtime (stdlib); pytest for tests |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (pure stdlib) |

## Findings

Full list in `findings.jsonl` (nothing at medium or above):

1. [low] test_coverage 0.95 — `main()`/`serve_forever()` launch shim uncovered (`app.py:134-138`); no behavioural gap
2. [info] Zero third-party runtime dependencies — stdlib WSGI + sqlite3 (`app.py:1-7`)
3. [info] Concurrency-safe shared SQLite connection under a threading.Lock (`app.py:17-19,65,75,87`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
grep -cE "^def test_" test_app.py                 # 6 tests
python -m pytest                                  # (optional) re-run: 6 passed
```
