# Evaluation: effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 33 effective test cases (24 `test_*` fns, one parametrized ×10) — all passed, 0 skipped; 93% line coverage
- **Build:** pass (test_coverage=0.93 from scores.json ⇒ imports + tests executed)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:341 _create_book`, `test_app.py:153` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:331 _list_books`, `test_app.py:188` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:162 list(author=)`, `test_app.py:197` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:335 _get_book`, `test_app.py:212,219` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:355 _update_book`, `test_app.py:225` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:370 _delete_book`, `test_app.py:258` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:110 BookRepository` (sqlite3), `test_app.py:133 persists_to_file` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py:225 _send_json`; 201/200/204/400/404/409/405 across handlers |
| R9 | Validation: title + author required | ✓ implemented | `app.py:66-77 validate_book`, `test_app.py:163,238` |
| R10 | GET /health health check | ✓ implemented | `app.py:324 _health`, `test_app.py:147` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` (Setup, Run, Test, API sections) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 24 functions, coverage=0.93 |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate output):

```text
test_coverage = 0.93   # imports succeeded, tests executed & passed, 93% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.87
```

Skip scan: `grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_app.py` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 414 |
| Lines of code (test_app.py) | 279 |
| Files (source + docs) | 4 (app.py, test_app.py, README.md, requirements-dev.txt) |
| Dependencies | 1 (pytest, test-only) |
| Tests total | 24 fns / ~33 cases |
| Tests effective | ~33 (0 skipped) |
| Skip ratio | 0% |
| Line coverage | 93% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Health 503 / DB-unavailable branch untested (coverage 93%, not 100%) — `app.py:327-329`
2. [info] ISBN uniqueness + format validation beyond spec — `app.py:89-99,125,349`
3. [info] Robust HTTP hardening beyond spec (413 guard, 405 Allow, case-insensitive filter) — `app.py:256,303,167`

No critical/high/medium findings: the run implements the full spec, tests pass with no skips, and the code is well-layered.

## Reproduce

```bash
cd experiments/adrianco/experiment-74-opus55-effort/rest-api-crud/runs/effort=high_language=python_model=claude-opus-5-5_prompt=neutral/rep3
cat scores.json                                              # stored mechanical scores
grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_app.py   # skip scan -> 0
# optional re-verify: pip install -r requirements-dev.txt && pytest
```
