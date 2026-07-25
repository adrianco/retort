# Evaluation: language=cpp · model=claude-fable-5 · prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all pass (8 integration test functions, ~40 CHECK assertions) / 0 failed / 0 skipped (8 effective)
- **Build:** pass — from `test_coverage=1.0`, `defect_rate=1.0` in scores.json (build + tests ran green)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (rest-api-crud, 12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.cpp:106` Post handler → `book_store.cpp:94 create`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/api.cpp:117` → `book_store.cpp:114 list()` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.cpp:118-119` reads param; `book_store.cpp:117` adds `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/api.cpp:127` → `get()`; 404 at `api.cpp:132` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/api.cpp:138` → `book_store.cpp:138 update`; 404 on no rows changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/api.cpp:159` → `book_store.cpp:163 remove`; 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/book_store.cpp:65-88` opens SQLite, `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `src/api.cpp:24 send_json`; 201/200/204/400/404/500/503 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `src/api.cpp:48-55` rejects missing/empty title/author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/api.cpp:98` returns 200 `{status:ok}` / 503 |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — Build/Run/deps/endpoints documented |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_api.cpp:214-221` — 8 test functions; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.7998, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.3375, "idiomatic": 0.93}
```

`test_coverage=1.0` ⇒ CMake build succeeded and CTest `api_tests` passed (the test
binary boots a real httplib server on an ephemeral port and exercises every route).
`code_quality=1.0`, `defect_rate=1.0`. `maintainability=0.3375` is the automated
LOC/complexity heuristic, not a defect signal.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests, excl. third_party) | 667 |
| Files (src + tests + CMake + README) | 8 |
| Dependencies | 2 vendored header-only (httplib, nlohmann/json) + system SQLite3 |
| Tests total | 8 functions (~40 assertions) |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored inline) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no deductions:

1. [info] Server binds to `0.0.0.0` (all interfaces) — `src/main.cpp:26`
2. [info] Store is thread-safe beyond spec (mutex + RAII prepared statements)
3. [info] Test suite exceeds the 3-test minimum with 8 integration tests

## Reproduce

```bash
cd runs/language=cpp_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                 # mechanical scores (build+test+lint), do not re-run
cat REQUIREMENTS.json           # ../../.. — pinned 12-item checklist
cmake -S . -B build && cmake --build build -j && ctest --test-dir build   # optional re-verify
```
