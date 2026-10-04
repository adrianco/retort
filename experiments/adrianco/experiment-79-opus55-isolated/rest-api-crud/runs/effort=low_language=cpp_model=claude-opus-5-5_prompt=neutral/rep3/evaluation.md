# Evaluation: rest-api-crud · effort=low language=cpp model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=cpp, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json` (`-Wall -Wextra`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean run. A dependency-free (beyond SQLite) C++17 service with a transport-independent
routing layer, hand-rolled HTTP/1.1 server and JSON parser, SQLite persistence with bound
parameters, and 11 tests (10 handler-level + 1 end-to-end over a real socket). Build, tests
and lint all pass per the stored mechanical scores.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.cpp` POST branch → `parse_book` + `store.create` → 201; `test_create_and_get` |
| R2 | GET /books lists all books | ✓ implemented | `src/api.cpp` GET `/books` → `store.list`; `test_list_and_author_filter` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.cpp:list` `WHERE author = ?`; `test_list_and_author_filter` (Frank Herbert → 2) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/api.cpp` `/books/` GET branch; `test_create_and_get`, `test_not_found_...` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `store.cpp:update` + api PUT branch; `test_update` (200 + 404 for missing) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `store.cpp:remove` + api DELETE → 204; `test_delete` |
| R7 | Data stored in SQLite | ✓ implemented | `src/store.cpp` uses `sqlite3_*`, `CREATE TABLE books`; `test_persistence_across_reopen` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/405/500 in `api.cpp`; `to_json`/`error`; e2e asserts raw status lines |
| R9 | Validation: title and author required | ✓ implemented | `parse_book` rejects missing/blank/non-string → 400; `test_validation` (12 bad payloads) |
| R10 | GET /health endpoint | ✓ implemented | `src/api.cpp` `/health` → `{"status":"ok"}`; `test_health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Requirements/Build/Run + env-var table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 11 tests in `tests/test_api.cpp`; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; no `retort.db` row yet):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.760, "idiomatic": 0.8, "token_efficiency": 0.097}
```

`test_coverage=1.0` ⇒ build succeeded and all tests passed. `code_quality=1.0` ⇒ lint clean.
Test harness (`main` in `tests/test_api.cpp`) runs 11 named tests and prints `N/11 tests passed`;
skip scan found 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 846 |
| Lines of code (tests) | 280 |
| Files (src + tests) | 10 |
| Dependencies | SQLite3 + Threads (2 `find_package`) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build | pass (`test_coverage=1.0`) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are info-level enhancements:

1. [info] E1 — End-to-end test over a real HTTP socket beyond the required unit tests
2. [info] E2 — SQL-injection safety explicitly asserted (`?author=x' OR '1'='1` → 0 rows)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=cpp_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                       # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json        # pinned R1–R12 checklist
grep -cE "CHECK|CHECK_EQ" tests/test_api.cpp   # assertion count
grep -cE "SKIP|skip|DISABLED" tests/test_api.cpp # skip scan → 0
# Optional full rebuild (not required; scores already stored):
#   cmake -S . -B build && cmake --build build && ctest --test-dir build
```
