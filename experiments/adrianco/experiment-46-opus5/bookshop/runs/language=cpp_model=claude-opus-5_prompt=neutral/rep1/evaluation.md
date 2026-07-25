# Evaluation: language=cpp_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=claude-opus-5, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 50 passed / 0 failed / 0 skipped (50 effective) — from `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` in `scores.json` (build + all tests ran)
- **Lint:** pass — `code_quality=1.0` in `scores.json` (compiled `-Wall -Wextra -Wpedantic`)
- **Architecture:** `run-summary` skill not available in this session — see inline notes below
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

Scores read from `scores.json` (inline gate): `code_quality=1.0`, `test_coverage=1.0`,
`defect_rate=1.0`, `maintainability=0.7295`, `idiomatic=0.88`, `token_efficiency=0.0073`.
No build/test/lint was re-run per the skill.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.cpp:86` POST route → `store.create`; `src/store.cpp:122` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `src/api.cpp:73` GET route → `store.list`; `src/store.cpp:153` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.cpp:74-78` reads `author` query; `src/store.cpp:156` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/api.cpp:94-107`; 404 at `:103` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/api.cpp:109-124`; `src/store.cpp:168` UPDATE, 404 when no rows changed |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/api.cpp:126-139` → `store.remove`; `src/store.cpp:185`; 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `src/store.cpp:3` `#include <sqlite3.h>`; schema `src/store.cpp:109-120` |
| R8 | JSON responses + correct status codes | ✓ implemented | `src/api.cpp:54-62` write_json/write_error; 201/204/400/404/405/500/503 covered |
| R9 | Validation: title & author required | ✓ implemented | `src/book.cpp:74-115` `validate_book_input`; required-string check `:18-39` |
| R10 | GET /health | ✓ implemented | `src/api.cpp:65-71`; `store.healthy()` `src/store.cpp:200` |
| R11 | README with setup & run | ✓ implemented | `README.md:1-40` (Requirements/Build/Run sections) |
| R12 | >= 3 tests | ✓ implemented | 50 `TEST(...)` cases across `tests/*.cpp`; `test_coverage=1.0` |

## Build & Test

Not re-run — scores taken from `scores.json` (per evaluate-run skill step 2):

```text
test_coverage = 1.0   # build succeeded + all tests executed and passed
code_quality  = 1.0   # compiled clean under -Wall -Wextra -Wpedantic
defect_rate   = 1.0   # build+test succeeded
```

Test suites (CMakeLists.txt `books_tests`): test_json, test_book, test_http, test_store,
test_api. Skip scan (`DISABLED_`/`GTEST_SKIP`/`#if 0`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests, .cpp/.hpp) | 3045 |
| Files (src + tests) | 20 |
| Dependencies | 2 system libs (SQLite3, pthreads); 0 third-party |
| Tests total | 50 |
| Tests effective | 50 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 5 findings are informational (enhancements beyond spec); none are defects:

1. [info] Author filter is case-insensitive and indexed (`src/store.cpp:157,119`)
2. [info] SQLite hardened: WAL + busy timeout + FULLMUTEX + RAII parameterized statements (`src/store.cpp:90-102`)
3. [info] Full status-code coverage incl. 201+Location, 204, 405 (`src/api.cpp:64-148`)
4. [info] 50 tests, zero skips; covers concurrency/unicode/keep-alive/oversized (`tests/test_api.cpp`)
5. [info] Zero third-party deps: hand-rolled HTTP/1.1 server + JSON parser (`CMakeLists.txt`, `src/http_server.cpp`, `src/json.cpp`)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-46-opus5/bookshop/runs/language=cpp_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                                   # stored build/test/lint scores
grep -rE "^\s*TEST\(" tests/*.cpp | wc -l          # 50 test cases
grep -rEn "DISABLED_|GTEST_SKIP|#if 0" tests/      # 0 skips
# optional rebuild:
cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure
```
