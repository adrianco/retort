# Evaluation: effort=low language=objc model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 21 assertions passed / 0 failed / 0 skipped (21 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (compiles clean; `defect_rate=1.0`, `test_coverage=1.0` from `scores.json`)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/BookAPI.m:98-109` INSERT + returns 201 |
| R2 | GET /books lists all | ✓ implemented | `src/BookAPI.m:96` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/BookAPI.m:91-95` WHERE author=? |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/BookAPI.m:117-118` returns book or 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/BookAPI.m:119-131` UPDATE + validation |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/BookAPI.m:132-138` DELETE, 204/404 |
| R7 | Data in SQLite | ✓ implemented | `src/BookAPI.m:2,21-28` sqlite3_open + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `src/BookAPI.m:11-17` Resp/Err; 201/200/204/400/404/405 |
| R9 | Validation: title+author required | ✓ implemented | `src/BookAPI.m:64-78` Validate() rejects blank/missing |
| R10 | GET /health | ✓ implemented | `src/BookAPI.m:86-87` returns {status:ok} |
| R11 | README with setup/run | ✓ implemented | `README.md` build/run/test + endpoint table |
| R12 | ≥3 tests | ✓ implemented | `tests/test_main.m` 21 CHECK assertions, `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality:     1.0
test_coverage:    1.0   (build + all tests passed)
defect_rate:      1.0   (build+test succeeded)
maintainability:  0.674
idiomatic:        0.38
```

Test harness (`tests/test_main.m`) runs every endpoint against an in-memory SQLite DB:
health, create, four validation-rejection cases, list, author filter, get (+404/+400),
update (+400/+404), delete (+204/+404), and 405/404 fallbacks. No skip/xfail mechanism
present; all 21 assertions are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 281 (BookAPI.m 194, test_main.m 61, BookAPI.h 14, main.m 12) |
| Files | 4 (3 src + 1 test) |
| Dependencies | 0 third-party (Foundation + libsqlite3 system libs) |
| Tests total | 21 assertions |
| Tests effective | 21 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json, not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] E1 — Validation rejects boolean-as-year and non-string isbn beyond spec (`src/BookAPI.m:73-76`)
2. [info] E2 — Handles 405 and 400-invalid-id beyond required status codes (`src/BookAPI.m:87,115`)
3. [info] N1 — HTTP server is one-request-per-connection (Connection: close) (`src/BookAPI.m:174,179`)

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=objc_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                       # mechanical scores (test_coverage=1.0, code_quality=1.0)
make                                  # build ./bookapi
make test                             # build + run tests/test_main.m (21 checks, 0 failures)
grep -rEc "skip|xfail" tests/ src/    # 0 skipped tests
```
