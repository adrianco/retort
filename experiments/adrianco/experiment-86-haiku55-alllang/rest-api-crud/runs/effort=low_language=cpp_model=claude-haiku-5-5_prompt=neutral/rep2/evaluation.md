# Evaluation: effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=cpp, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from `scores.json` (`test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=0.9833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (not re-run): `test_coverage=1.0`, `code_quality=0.9833`,
`defect_rate=0.9703`, `maintainability=0.8867`, `idiomatic=0.8`, `token_efficiency=0.0421`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.cpp` `server.Post("/books", …)` → `repository.create`; `database.cpp:BookRepository::create` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `src/api.cpp` `server.Get("/books", …)`; `database.cpp:list` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.cpp` reads `author` param; `database.cpp:list` adds `WHERE author = ?`; test `http_list_supports_author_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/api.cpp` `R"(/books/([^/]+))"` → `repository.find`, 404 on miss |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/api.cpp` Put handler → `database.cpp:update`, 404 when no row changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/api.cpp` Delete handler → `database.cpp:remove`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/database.cpp` uses `sqlite3_*`; schema `CREATE TABLE books …` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `send_json`/`send_error`; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title and author required | ✓ implemented | `src/validation.cpp:required_text`; test `http_rejects_invalid_input` (400) |
| R10 | GET /health health check | ✓ implemented | `src/api.cpp` `server.Get("/health", …)` returns `{"status":"ok"}`; test `http_health_check` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Requirements, Build, Run sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_books.cpp` — 11 `TEST(...)` cases; `test_coverage=1.0` |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: test_coverage=1.0  ⇒  CMake build + all tests passed
scores.json: code_quality=0.9833 (lint/quality)
```

```text
tests/test_books.cpp — self-contained runner, 11 cases:
  repository_create_and_find, repository_optional_fields_round_trip_as_null,
  repository_list_filters_by_author, repository_update_and_remove,
  validation_accepts_valid_body, validation_requires_title_and_author,
  validation_rejects_bad_year_and_non_object_body,
  http_health_check, http_book_crud_lifecycle,
  http_list_supports_author_filter, http_rejects_invalid_input
  → 0 skipped, 0 disabled
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests + CMake) | 865 |
| Files (src + tests + CMake + README) | 10 |
| Dependencies | 3 (cpp-httplib, nlohmann/json, SQLite3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Validation goes beyond spec: year bounds (0–9999) and all-errors accumulation
2. [info] GET /books/{id} returns 400 for non-integer ids before the 404 path

No correctness, build, test, or requirement defects found.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                    # stored build/test/lint scores
cat ../../REQUIREMENTS.json                         # pinned 12-requirement checklist
grep -cE '^TEST\(' tests/test_books.cpp             # 11 test cases
grep -rnE 'DISABLED_|GTEST_SKIP' tests/             # 0 skips
# Build + test (only if re-verifying): cmake -S . -B build && cmake --build build && ctest --test-dir build
```
