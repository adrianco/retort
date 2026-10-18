# Evaluation: agent=codex effort=low language=cpp model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=cpp, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** passed (test_coverage=1.0 from scores.json) / 0 failed / 0 skipped — 1 CTest target, 9 assertions (effective)
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=1.0); not re-run
- **Lint:** pass — code_quality=1.0 from scores.json (built with `-Wall -Wextra -Wpedantic`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `book_api.cpp:196-206` INSERT + 201 echo |
| R2 | GET /books lists all books | ✓ implemented | `book_api.cpp:184-194` SELECT all ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `book_api.cpp:187-190` parses author param, `WHERE author=?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `book_api.cpp:211-215` 200/404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `book_api.cpp:217-227` UPDATE, 404 if no rows changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `book_api.cpp:228-234` DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `book_api.cpp:168-176` sqlite3_open + CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/500 throughout; `main.cpp:38` Content-Type json |
| R9 | Validation: title and author required | ✓ implemented | `book_api.cpp:136-137` reject empty/blank (400); test `tests.cpp:15-16` |
| R10 | GET /health endpoint | ✓ implemented | `book_api.cpp:180` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` build/test/run + API docs |
| R12 | >= 3 unit/integration tests | ✓ implemented | `tests.cpp` 9 assertions across all routes; test_coverage=1.0 |

No requirement is partial or missing. Enhancements beyond spec: strict `year` integer validation (0–9999), URL-decoding of query params, bespoke strict JSON parser, SQL-injection-safe prepared statements.

## Build & Test

Not re-run — stored mechanical scores used per skill policy.

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.0309, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.5019, "idiomatic": 0.35}
```

test_coverage=1.0 ⇒ `cmake --build` + `ctest` succeeded and all assertions passed.
Build uses `find_package(SQLite3 REQUIRED)` and `-Wall -Wextra -Wpedantic` (CMakeLists.txt).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 364 (book_api.cpp 241, main.cpp 56, tests.cpp 36, book_api.hpp 31) |
| Files (source) | 5 (3 code + hpp + CMakeLists) |
| Dependencies | 1 (SQLite3) |
| Tests total | 1 CTest target / 9 assertions |
| Tests effective | 9 assertions (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Unsupported method on a valid resource returns 404, not 405 (`reason_phrase(405)` defined but never emitted)
2. [low] Tests are one CTest target with 9 assertions rather than discrete named cases
3. [info] `?author=` filter is exact-match only (SQL equality)
4. [info] `year` validation stricter than spec (integers 0–9999, rejects floats/booleans)

No correctness, build, or missing-requirement issues found.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=cpp_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (build/test/lint)
cat TASK.md ../../../REQUIREMENTS.json
# Build & test (only if re-verifying; not required):
cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
```
