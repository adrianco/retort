# Evaluation: rest-api-crud · effort=medium language=python model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=medium (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 49 passed / 0 failed / 0 skipped (49 effective)
- **Build:** pass — deps import cleanly (test_coverage=0.97, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

All requirement classifications are backed by the pinned checklist in `../../../REQUIREMENTS.json` (12 fixed requirements). Mechanical scores are read from `scores.json` (inline gate output); the run was not yet present in `retort.db`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:206-210` → `BookStore.create` `app.py:65-71`; `test_app.py:90` |
| R2 | GET /books lists all | ✓ implemented | `app.py:203-205` → `BookStore.list` `app.py:73-81`; `test_app.py:162` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:204`, `app.py:76-78` (COLLATE NOCASE); `test_app.py:171` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `app.py:218-219,227-229`; `test_app.py:188,196` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:220-222` → `BookStore.update` `app.py:87-95`; `test_app.py:202` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:223-225` → `BookStore.delete` `app.py:97-100`; `test_app.py:244` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:23-31,54-59` sqlite3; `test_app.py:290` persistence across instances |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:233-253` (201/200/204/400/404/405/409/413/500); `test_app.py` throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:109-142` validate_book; `test_app.py:109-130` |
| R10 | GET /health | ✓ implemented | `app.py:197-200`; `test_app.py:83` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, API sections) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 49 tests pass; `test_app.py` |

## Build & Test

```text
# tests (from _agent_stdout.log)
python -m pytest
49 passed in 0.61s
```

```text
# scores.json (inline gate)
test_coverage = 0.97   (tests ran, high coverage)
defect_rate   = 1.0    (build + tests succeeded)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.76
token_efficiency = 0.0678
```

No build/test/lint was re-run — mechanical scores taken from `scores.json` per the evaluate-run skill.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 616 (app.py 278, test_app.py 338) |
| Files (source) | 4 (app.py, test_app.py, README.md, requirements-dev.txt) |
| Runtime dependencies | 0 (stdlib only) |
| Test-only dependencies | 1 (pytest>=8) |
| Tests total | 49 |
| Tests effective | 49 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] ISBN uniqueness enforced with 409 Conflict beyond spec
2. [info] Request-body size cap and Content-Length hardening
3. [info] SQL-injection-safe parameterized queries and literal ?author= matching
4. [info] Real end-to-end HTTP test through an actual socket
5. [info] PUT uses full-replace semantics for optional fields (correct REST PUT)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=medium_language=python_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                      # mechanical scores (inline gate)
python -m pytest                     # 49 passed
python app.py                        # serve on http://127.0.0.1:8000
```
