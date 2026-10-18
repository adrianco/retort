# Evaluation: rest-api-crud · effort=low language=objc model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions, all effective (0 skipped); `test_coverage=1.0` ⇒ build + all tests passed
- **Build:** pass (per `scores.json` `test_coverage=1.0` / `defect_rate=1.0`; not re-run)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookAPI.m:152 createBookWithBody:` → `BookStore.m:53 createBookWithFields:`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `BookAPI.m:137 listBooksWithQuery:` → `BookStore.m:67 booksWithAuthor:nil` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookAPI.m:84 AuthorFilterFromQuery` + `BookStore.m:69` `WHERE author = ?` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `BookAPI.m:144 getBookWithID:` returns 404 when nil (`:148`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookAPI.m:164 updateBookWithID:body:` → `BookStore.m:74`, 200/404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookAPI.m:176 deleteBookWithID:` returns 204, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.m:2 #import <sqlite3.h>`, `:39` CREATE TABLE, prepared statements |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `APIResponse` + `HTTPServer.m:179 writeResponse:` Content-Type application/json; 200/201/204/400/404/405/413/422/500 |
| R9 | Validation: title and author required | ✓ implemented | `BookAPI.m:52-53 NormalizedBookFields` rejects blank title/author (422); see info finding on 422 vs 400 |
| R10 | GET /health endpoint | ✓ implemented | `BookAPI.m:113-116` returns 200 `{"status":"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — build/test/run, env vars, endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_main.m` — 6 test functions incl. end-to-end socket test |

## Build & Test

Not re-run — stored mechanical scores used per skill policy (`scores.json`):

```text
code_quality=1.0  test_coverage=1.0  defect_rate=1.0
maintainability=0.7615  idiomatic=0.82  token_efficiency=0.0336
```

`test_coverage=1.0` is the build+test signal: `make test` compiled (`clang -fobjc-arc ... -framework Foundation -lsqlite3`) and all assertions passed. Test harness is a self-contained CHECK-macro runner (`tests/test_main.m:211 main`) exercising create/fetch, validation, list+filter, update/delete, health/routing, and one end-to-end run over a real loopback socket. No skipped/disabled tests (the `xit(` grep hit was a false positive on `exit(1)`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 890 (`wc -l` over src/*.{m,h}, tests/*.m) |
| Files | 8 (6 source/header + test + Makefile not counted here) |
| Dependencies | 0 third-party (Foundation + libsqlite3 system libs only) |
| Tests total | 6 functions |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are info-level (nothing above `low`):

1. [info] R9 — validation failures return 422, not the 400 named in `REQUIREMENTS` how_to_verify; 422 is appropriate and spec mandates only "appropriate status codes".
2. [info] Server handles one connection at a time (documented; fine for the task).
3. [info] Validation beyond spec — rejects boolean/float year and non-string isbn (enhancement).

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json      # pinned 12-requirement checklist
make test                        # re-run only if scores.json absent (clang + sqlite3)
```
