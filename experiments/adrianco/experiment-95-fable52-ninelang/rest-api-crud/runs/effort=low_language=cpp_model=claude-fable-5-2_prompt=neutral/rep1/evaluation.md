# Evaluation: rest-api-crud · effort=low language=cpp model=claude-fable-5-2 prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=claude-fable-5-2, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — via `test_coverage=1.0`
- **Build:** pass (`test_coverage=1.0` ⇒ build + all tests ran) — from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Clean run. A C++17 service implementing the full CRUD spec with real SQLite
persistence, a from-scratch HTTP server and JSON parser (zero third-party deps
beyond SQLite), and an 11-case test suite that exceeds the 3-test minimum.
Stored mechanical scores: `test_coverage=1.0`, `code_quality=1.0`,
`defect_rate=1.0`, `maintainability=0.75`, `idiomatic=0.60`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.cpp:83-88` POST branch → `store.create`; `store.cpp:75` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `app.cpp:71-82` GET branch; `store.cpp:85` SELECT ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.cpp:72-73` reads `author` query; `store.cpp:88` `WHERE author = ?` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.cpp:96-99`, 404 at `app.cpp:98`; `store.cpp:100` get |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.cpp:101-108`; `store.cpp:112` UPDATE, 404 on no-change |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.cpp:109-112` (204); `store.cpp:121` DELETE |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.cpp:3` `#include <sqlite3.h>`; schema `store.cpp:57-64`; CMake links SQLite3 |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/400/405/204/500 across `app.cpp`; `Content-Type: application/json` asserted `tests/test_main.cpp:230` |
| R9 | Validation: title and author required | ✓ implemented | `app.cpp:20-32` `requiredString` rejects missing/null/blank/non-string → 400 |
| R10 | GET /health endpoint | ✓ implemented | `app.cpp:65-68` returns `{"status":"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Requirements/Build/Run/Test + env-var table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_main.cpp` — 11 tests; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill policy):

```text
test_coverage = 1.0   # build succeeded + all tests executed and passed
code_quality  = 1.0   # lint/quality gate clean
defect_rate   = 1.0   # build+test succeeded
```

```text
tests/test_main.cpp — 11 test cases, no skips:
  health, create and get, optional fields, validation, list and author filter,
  update, delete, not found / method not allowed, json escaping and sql safety,
  persistence across reopen, end-to-end over HTTP
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 1157 |
| Files (excl. build-warn/.git) | 20 |
| Dependencies | SQLite3 + pthreads (no third-party libs) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level; no defects:

1. [info] End-to-end TCP + persistence-across-reopen tests beyond the 3-test minimum
2. [info] JSON-escaping / SQL-injection safety explicitly tested
3. [info] No OpenAPI/schema doc, only prose README (not required by spec)

## Reproduce

```bash
cd experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=cpp_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                      # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json       # pinned 12-item checklist
# build + test (only if re-verifying; scores already stored):
cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
```
