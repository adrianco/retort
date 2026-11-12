# Evaluation: effort=low_language=objc_model=claude-fable-5-2_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 test groups (56 CHECK assertions) passed / 0 failed / 0 skipped (8 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — `clang -fobjc-arc` via Makefile (from `test_coverage=1.0`/`defect_rate=1.0`, not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json (`-Wall -Wextra`, no warnings reported)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BooksAPI.m:325` POST branch → `BookStore.m:108 createBookWithTitle:`; test `TestCreateAndGet` |
| R2 | GET /books lists all books | ✓ implemented | `BooksAPI.m:322` → `BookStore.m:124 booksFilteredByAuthor:nil`; `TestListAndAuthorFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookStore.m:129` `WHERE author = ? COLLATE NOCASE`; `TestListAndAuthorFilter` (Jane Austen → 2) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `BooksAPI.m:345` → `bookWithID:`; returns 404 at `:347`; `TestDeleteAndNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BooksAPI.m:349` → `BookStore.m:147 updateBookWithID:`; `TestUpdate` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BooksAPI.m:358` → `BookStore.m:164 deleteBookWithID:`; 204/404; `TestDeleteAndNotFound` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.m:36` `#import <sqlite3.h>`, schema at `:46`; `TestPersistenceOnDisk` reopens an on-disk DB |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `BooksAPI.m:220 Respond()`; 201/200/204/404/405/422/400 used; `HTTPServer.m:395 ReasonPhrase` |
| R9 | Input validation: title & author required | ✓ implemented | `BooksAPI.m:271-282` rejects missing/blank title/author (422); `TestValidation`. See info finding: 422 not 400 |
| R10 | GET /health health check | ✓ implemented | `BooksAPI.m:315` → `BookStore.m:177 isHealthy` (runs `SELECT 1`); `TestHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build/run/test, env vars, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_main.m` — 8 test functions, 56 CHECK assertions; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.8217, "idiomatic": 0.6, "token_efficiency": 0.0668}
```

`test_coverage=1.0` ⇒ `make test` built with clang (`-fobjc-arc -Wall -Wextra`, Foundation + libsqlite3) and all 8 test groups passed. `defect_rate=1.0` and `code_quality=1.0` corroborate a clean build with no lint warnings. 0 skipped/disabled tests (grep of src+tests for skip markers = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 576 (src .m/.h) |
| Test LOC | 239 |
| Files | 8 (4 modules ×2 + main + test) |
| Dependencies | 0 third-party (Foundation, libsqlite3, BSD sockets — all system) |
| Tests total | 8 groups / 56 CHECK assertions |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] R9 rejects missing title/author with 422 rather than the 400 named in the verifier text — a semantically appropriate rejection code; request is still correctly rejected (malformed JSON does return 400).
2. [info] Enhancement: SQL fully parameterised; an injection payload is explicitly tested to return 0 rows.
3. [info] Enhancement: transport/router separation (`BooksAPI` is socket-independent) enables fast unit tests plus one real-socket end-to-end test.

## Reproduce

```bash
cd "experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=objc_model=claude-fable-5-2_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build/test/lint) — not re-run
make test                  # optional: clang -fobjc-arc, runs all 8 test groups
grep -rE "Skip|xit\(|\.skip\(|DISABLED" src tests | wc -l   # skip count = 0
```
