# Evaluation: effort=low language=cpp model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — from `test_coverage=1.0`
- **Build:** pass (from `scores.json` `test_coverage=1.0` — build+tests ran; not re-run)
- **Lint:** pass — `code_quality=1.0`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info enhancements)

Scores sourced from `scores.json` (inline gate; run not yet in `retort.db`):
`test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.699`, `idiomatic=0.4`, `token_efficiency=0.0216`.

## Requirements

Using the pinned `REQUIREMENTS.json` checklist (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/api.cpp:90 create_book` → 201; `repository.cpp:90 insert` |
| R2 | GET /books lists all | ✓ implemented | `src/api.cpp:81 list_books`; `repository.cpp:111 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.cpp:82 query_param("author")`; `repository.cpp:113 WHERE author=?1` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `src/api.cpp:95 get_book` → 404; `repository.cpp:102 find` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/api.cpp:103 update_book`; `repository.cpp:129 update` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/api.cpp:112 delete_book` → 204; `repository.cpp:145 remove` |
| R7 | Data stored in SQLite | ✓ implemented | `src/repository.cpp:5 #include <sqlite3.h>`, schema at `:67`, prepared statements |
| R8 | JSON responses + correct codes | ✓ implemented | `src/api.cpp` Response{status,json}; 201/200/404/400/405/409/204/500 |
| R9 | title & author required | ✓ implemented | `src/book.cpp:26 required_string` → 400; tests `api_tests.cpp:54` |
| R10 | GET /health | ✓ implemented | `src/api.cpp:128` → 200 `{status,database}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Prerequisites/Build/Run/Test/API |
| R12 | >= 3 tests | ✓ implemented | `tests/api_tests.cpp` — 9 test cases; `test_coverage=1.0` |

No prompt-factor requirements (`prompt=neutral` is not a `prompts/<level>.md` instruction file; TASK.md is the whole spec).

## Build & Test

Not re-run — stored scores used per skill policy.

```text
scores.json: test_coverage=1.0  => build + all tests passed
             code_quality=1.0   => lint/quality clean
             defect_rate=1.0    => build+test succeeded
```

Test suite (Boost.Test, in-memory SQLite): 9 cases — health, create+get round-trip, required-field rejection, malformed-JSON/bad-optional rejection, duplicate-isbn 409, author filter (exact, URL-decoded), PUT replace + 404 + 400, delete + re-delete 404, unknown-route/id 404 + wrong-method 405. No `disabled()`/commented tests found (0 skips).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + CMake) | 790 |
| Source files (src + tests + CMake) | 9 |
| Dependencies | Boost (json, unit_test_framework), SQLite3 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 4 findings are `info`-level enhancements beyond spec — no defects, no missing/partial requirements, no skipped tests:

1. [info] Duplicate-ISBN conflict returns 409 (`repository.cpp:94`)
2. [info] Method-not-allowed handling returns 405 (`api.cpp:129,142,160`)
3. [info] ISBN shape + year-range validation beyond required fields (`book.cpp:54,62`)
4. [info] Socket-free testable core enables 9 integration tests (`api_tests.cpp`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                               # stored mechanical scores (build+test+lint)
grep -cE "BOOST_(AUTO|FIXTURE)_TEST_CASE" tests/api_tests.cpp   # test count: 9
# Optional full rebuild (not required; scores are authoritative):
# cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
```
