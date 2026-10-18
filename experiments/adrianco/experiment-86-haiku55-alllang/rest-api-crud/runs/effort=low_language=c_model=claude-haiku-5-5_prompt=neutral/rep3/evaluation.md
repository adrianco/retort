# Evaluation: effort=low_language=c_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=c, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 suites (test_json, test_validation, test_crud, test_http) — all passing / 0 failed / 0 skipped
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests ran green)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

A clean, idiomatic C11 implementation. Build and tests pass per the stored mechanical
scores (`scores.json`: test_coverage=1.0, code_quality=1.0, defect_rate=1.0,
idiomatic=0.86, maintainability=0.61). All twelve pinned requirements are satisfied with
concrete evidence; no skipped or disabled tests.

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.c:create_book` → `book_insert`; `src/book.c:book_from_json` reads all four fields |
| R2 | GET /books lists all books | ✓ implemented | `src/api.c:list_books` → `book_list`; emits JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.c:query_param`+`url_decode`; `src/book.c:book_list` SQL `WHERE ?1 IS NULL OR author = ?1` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/api.c:get_book`; `book_find` returns 0→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/api.c:update_book` → `book_update`; 404 when no rows changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/api.c:delete_book` → `book_delete`; 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `src/book.c:db_open` + prepared statements; `src/book.h` includes `sqlite3.h` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `src/api.c` 201/200/204/400/404/405/500; `write_book`/`api_error` build JSON; `status_text` |
| R9 | Validation: title and author required | ✓ implemented | `src/book.c:text_field`+`is_blank` reject missing/blank → 400; test_validation cases |
| R10 | GET /health health check | ✓ implemented | `src/api.c:api_handle` `/health` → `{"status":"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` build/run/test + dependency install per-OS |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_api.c` 4 suites, dozens of CHECK assertions; test_coverage=1.0 |

No enhancements counted against spec; three noted as informational (see Findings).

## Build & Test

Not re-run — stored mechanical scores are authoritative per the evaluate-run skill.

```text
scores.json
test_coverage = 1.0   (build + all tests passed)
code_quality  = 1.0
defect_rate   = 1.0
idiomatic     = 0.86
maintainability = 0.61
```

Test harness (`make test`) builds `bin/test_api` and runs four suites; `main()` returns
nonzero on any failed CHECK, so test_coverage=1.0 implies all checks passed.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1355 |
| Lines of code (tests) | 315 |
| Files (src + tests) | 12 |
| Dependencies | SQLite3 + libpthread (system libs; no package manifest) |
| Test suites | 4 |
| Tests effective | 4 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (stored score) |

## Findings

All informational (no deductions):

1. [info] Hand-written JSON parser with full `\uXXXX` + surrogate-pair handling (`src/json.c`)
2. [info] ISBN-10/13 format validation and `?author=` URL-decoding with 400 on bad encoding (`src/book.c:34`, `src/api.c:20`)
3. [info] End-to-end HTTP test over a live socket (`tests/test_api.c:238`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                      # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json          # pinned requirement checklist
make && make test                    # (optional) rebuild + run the 4 test suites
```
