# Evaluation: effort=default_language=python_model=claude-fable-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from scores.json (test_coverage=0.96, defect_rate=1.0)
- **Lint:** pass — code_quality=0.789 (idiomatic=0.78)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:94-110` create_book, INSERT of all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:112-123` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:116-120` COLLATE NOCASE author filter |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:125-130` get_book, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:132-155` update_book (partial updates) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:157-164` delete_book, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:9-31` SQLite schema + connection |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:48-88,99-101` validate_payload require_all |
| R10 | GET /health | ✓ implemented | `app.py:90-92` health returns {"status":"ok"} |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, API, tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 7 tests, test_coverage=0.96 |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill):

```text
test_coverage = 0.96   # build + tests executed and passed
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.789
maintainability = 1.0
idiomatic     = 0.78
```

7 test functions in `test_app.py`, 0 skips (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 300 (app.py 179 + test_app.py 121) |
| Files | 9 (incl. .coverage, logs) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Clean full-spec implementation, all 12 requirements met
2. [info] Partial-update semantics + case-insensitive author filter beyond spec
3. [low] code_quality below 1.0 (0.789) — minor style items, no functional impact

No critical/high/medium findings. Run passes the conformance gate.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=default_language=python_model=claude-fable-5_prompt=neutral/rep3
cat scores.json
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
grep -cE "^def test_" test_app.py
# optional re-run: python3 -m pytest -v
```
