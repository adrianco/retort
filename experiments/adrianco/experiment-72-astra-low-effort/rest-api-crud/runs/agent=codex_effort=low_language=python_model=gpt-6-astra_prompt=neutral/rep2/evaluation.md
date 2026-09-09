# Evaluation: rest-api-crud · agent=codex effort=low model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** pass (test_coverage=0.93, defect_rate=1.0 from scores.json) — 5 test functions, 15 effective cases, 0 skipped
- **Build:** pass — defect_rate=1.0 (build+tests ran and passed; scores.json)
- **Lint:** pass — code_quality=0.79 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate output) — build/test/lint were NOT re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:120-123` INSERT + 201 with Location |
| R2 | GET /books lists all | ✓ implemented | `app.py:116-118` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:113-115` filters by author param |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:101-106`; 404 at `:104` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:110-111` UPDATE; re-reads row |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:107-109` DELETE + {deleted:id} |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:29` sqlite3.connect; table at `:22-25` |
| R8 | JSON + appropriate status codes | ✓ implemented | `app.py:45-48` JSON body; 201/200/404/400/405/413/415/503 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:70-73` rejects blank/non-string (400) |
| R10 | GET /health | ✓ implemented | `app.py:83-88` returns {status:ok}, pings DB |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, curl, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 5 functions / 15 cases; coverage 0.93 |

## Build & Test

Not re-run per skill policy — stored scores used:

```text
scores.json: test_coverage=0.93, defect_rate=1.0, code_quality=0.789,
             maintainability=0.987, idiomatic=0.80
```

`defect_rate=1.0` ⇒ build + tests executed and passed. `test_coverage=0.93` ⇒ tests ran with 93% line coverage.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 218 (app.py 135, test_app.py 83) |
| Files | 2 source (app.py, test_app.py) + README |
| Dependencies | 1 dev (pytest); 0 runtime (stdlib only) |
| Tests total | 5 functions / 15 parametrized cases |
| Tests effective | 15 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no deductions:

1. [info] Defensive input handling beyond spec (415/413, unknown-field rejection, 64-bit year range) — `app.py:52,60,68,75`
2. [info] SQL-injection safety explicitly tested — `test_app.py:62`
3. [info] Central DB-error handling returns 503 — `app.py:43-44`

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skip count -> 0
grep -cE "^def test_" test_app.py                 # test function count -> 5
# Requirements checklist from ../../REQUIREMENTS.json (pinned, 12 items)
```
