# Evaluation: agent=claude-code_language=cpp_model=claude-opus-4-8_prompt=neutral_stack=m80 · rep 1

## Summary

- **Factors:** language=cpp, model=claude-opus-4-8, agent=claude-code, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 test functions (many CHECK assertions) passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build + tests ran and passed)
- **Lint:** pass — `code_quality=0.983` in scores.json
- **Architecture:** run-summary skill unavailable in this session — see Build & Test / Requirements below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist pinned from `bookshop/REQUIREMENTS.json` (12 fixed requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/main.cpp:59` → `src/handlers.cpp:48 handle_create` → `src/book_store.cpp:104 create` (201) |
| R2 | GET /books lists all books | ✓ implemented | `src/main.cpp:64` → `src/handlers.cpp:60 handle_list` → `src/book_store.cpp:127 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.cpp:65-67` reads param; `src/book_store.cpp:129-140` adds `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/main.cpp:71` → `src/handlers.cpp:75 handle_get` returns 404 when `!book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/main.cpp:81` → `src/handlers.cpp:87 handle_update` → `src/book_store.cpp:167 update` (404 if no rows) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/main.cpp:91` → `src/handlers.cpp:102 handle_delete` → `src/book_store.cpp:194 remove` (204 / 404) |
| R7 | Data stored in SQLite | ✓ implemented | `src/book_store.cpp:3 #include <sqlite3.h>`, `:87 init_schema` real `books` table; `CMakeLists.txt:8 find_package(SQLite3)` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `src/book.h:16 book_to_json`; codes 201/200/404/400/204/500 across `src/handlers.cpp` |
| R9 | Validation: title and author required | ✓ implemented | `src/book_store.cpp:18-30 validate` throws → 400; test `test_validation_requires_title_and_author` (tests/test_main.cpp:74) |
| R10 | GET /health health check | ✓ implemented | `src/main.cpp:51-56` returns `{"status":"ok"}` 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (endpoints table, build/run, deps documented) |
| R12 | >= 3 unit/integration tests | ✓ implemented | 7 tests in `tests/test_main.cpp:242-248`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage   = 1.0     # build + all tests passed
code_quality    = 0.9833
defect_rate     = 0.9993
maintainability = 0.3380
idiomatic       = 0.87
token_efficiency= 0.6891
```

Test structure (`tests/test_main.cpp`) — a lightweight custom CHECK harness:

```text
TEST: create_and_get
TEST: validation_requires_title_and_author
TEST: list_with_author_filter
TEST: update
TEST: delete
TEST: optional_fields_null_in_json
TEST: http_end_to_end        # real httplib server + client round-trip
ALL TESTS PASSED
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests, excl. vendored third_party) | 816 |
| — source (src/) | 558 |
| — tests (tests/) | 258 |
| Files (src + tests) | 7 |
| Dependencies | SQLite3 (system); httplib + nlohmann/json vendored under third_party/ |
| Tests total | 7 functions |
| Tests effective | 7 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (scored inline) |

## Findings

3 info-level items (full list in `findings.jsonl`); no correctness, build, or test defects:

1. [info] Input validation exceeds spec — type checks + whitespace trimming (`src/handlers.cpp:27`, `src/book_store.cpp:18`)
2. [info] Full HTTP round-trip integration test beyond unit tests (`tests/test_main.cpp:161`)
3. [info] `maintainability=0.338` low — likely a size artifact of vendored single-header libs, not a code-quality issue

## Reproduce

```bash
cd experiments/adrianco/experiment-43-morelangs/bookshop/runs/agent=claude-code_language=cpp_model=claude-opus-4-8_prompt=neutral_stack=m80/rep1
cat scores.json                       # stored build/test/lint scores (not re-run)
cmake -S . -B build && cmake --build build   # build (book_api + book_tests)
ctest --test-dir build --output-on-failure   # run tests
```
