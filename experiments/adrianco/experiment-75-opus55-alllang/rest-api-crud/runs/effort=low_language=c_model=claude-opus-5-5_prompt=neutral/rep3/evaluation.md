# Evaluation: effort=low_language=c_model=claude-opus-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=c, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 30 checks passed / 0 failed / 0 skipped (30 effective; 5 test functions)
- **Build:** pass — clean under `-Wall -Wextra` (test_coverage=1.0, defect_rate=1.0 from scores.json)
- **Lint:** pass — 0 warnings (code_quality=1.0 from scores.json); tests also clean under ASan+UBSan
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/books.c:251 create_book` INSERT, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/books.c:219 list_books` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/books.c:224` parses author, `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/books.c:191 get_book`, 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/books.c:271 update_book`, 404 on 0 changes |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/books.c:293 delete_book`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/books.c:169 books_init_db`, sqlite3 prepared stmts |
| R8 | JSON responses + status codes | ✓ implemented | `src/main.c:28 reply` sets Content-Type json; 200/201/204/400/404/405 |
| R9 | Validation: title+author required | ✓ implemented | `src/books.c:255,275 blank()` check → 400 "required" |
| R10 | GET /health endpoint | ✓ implemented | `src/books.c:309` returns 200 `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, endpoints, curl examples |
| R12 | At least 3 tests | ✓ implemented | `tests/test_books.c` — 5 test fns, 30 checks, 0 failures |

No requirements missing or partial. Enhancements beyond spec: URL-decoding of the
author filter, `Payload Too Large` (413) guard, JSON string escaping, and
ASan/UBSan-instrumented tests.

## Build & Test

Not re-run — stored mechanical scores read from `scores.json`
(`test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`). The build/test
transcript in `_agent_stdout.log` confirms:

```text
cc -std=c11 -Wall -Wextra -O2 ... -o books_server src/main.c src/books.c -lsqlite3
cc -std=c11 -Wall -Wextra -O2 ... -fsanitize=address,undefined -g -o test_books tests/test_books.c src/books.c -lsqlite3
./test_books
30 checks, 0 failures
```

Build is warning-clean at `-Wall -Wextra`; tests pass with no sanitizer
diagnostics.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 437 (books.c 330, main.c 94, books.h 13) |
| Lines of code (tests) | 90 |
| Files (source, excl. build artifacts) | 6 |
| Dependencies | 1 (system libsqlite3) |
| Tests total | 30 checks (5 functions) |
| Tests effective | 30 |
| Skip ratio | 0% |
| Build duration | not measured (scores read from cache) |

## Findings

All findings are low/info; full list in `findings.jsonl`:

1. [low] Unknown JSON keys silently ignored instead of rejected (`src/books.c:137-148`)
2. [low] `year` parsed via `strtod`+cast can overflow silently (`src/books.c:129-131`)
3. [info] PUT uses full-replace semantics with POST-style validation (`src/books.c:271-291`)
4. [info] Tests run under ASan+UBSan, clean (`Makefile:12`, `_agent_stdout.log`)

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-opus-5-5_prompt=neutral/rep3
cat scores.json                 # stored mechanical scores (no re-run)
make && make test               # build server + run sanitized tests → "30 checks, 0 failures"
```
