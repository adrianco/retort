# Evaluation: effort=low language=objc model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=objc, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate): `test_coverage=1.0`, `code_quality=1.0`,
`defect_rate=1.0`, `maintainability=0.806`, `idiomatic=0.60`, `token_efficiency=0.022`.
Build/test/lint were **not** re-run — stored scores stand in.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/BookAPI.m:createBook:` → `BookStore.m:insertBook:`; test `testAPICreateReadUpdateDelete` (201 + Location) |
| R2 | GET /books lists all books | ✓ implemented | `src/BookAPI.m:listBooks:` → `booksByAuthor:nil`; test `testAPIListAndAuthorFilter` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/BookAPI.m:listBooks:` reads `request.query[@"author"]`; `BookStore.m:booksByAuthor:` (COLLATE NOCASE); tests `testStoreAuthorFilter`, `testAPIListAndAuthorFilter` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/BookAPI.m:getBook:` returns 200/404; test asserts 200, 404, and 400 on `/books/abc` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/BookAPI.m:updateBook:request:` (merge) → `BookStore.m:updateBook:`; test asserts 200 + merged fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/BookAPI.m:deleteBook:` → `deleteBookWithID:`; test asserts 204 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/BookStore.m` uses `sqlite3_open_v2`, parameterized statements; `Makefile` links `-lsqlite3` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `HTTPMessage.m:responseWithStatus:json:`; 201/200/204/400/404/405/413/500 used throughout `BookAPI.m` |
| R9 | Validation: title and author required | ✓ implemented | `src/Book.m:bookFromDictionary:error:` rejects empty/missing title/author (400); test `testAPIErrorResponses` |
| R10 | GET /health endpoint | ✓ implemented | `src/BookAPI.m:handleRequest:` returns `{status:ok}`; test `testHealthEndpoint` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — build/test/run, env vars, endpoints, data model |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/main.m` — 8 test cases, all pass (test_coverage=1.0) |

No requirement is partial or missing. No enhancements beyond spec affect scoring.

## Build & Test

Not re-run — stored scores used (per skill step 2).

```text
scores.json: test_coverage=1.0  ⇒ `make test` built + ran all tests, all passed
             code_quality=1.0   ⇒ lint clean
             defect_rate=1.0    ⇒ build+test succeeded
```

Test runner (`tests/main.m`) executes 8 cases over the model, store, API router, and the
live socket server (`testServerOverSocket` binds an ephemeral port and issues real HTTP).
No `skip`/`disabled`/`XCTSkip` markers found (grep: 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, src/ + tests/) | 1106 |
| Source modules (.h/.m under src/) | 11 files / 6 modules |
| Test files | 1 (`tests/main.m`) |
| Dependencies (third-party) | 0 (Foundation + libsqlite3, both system) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | not re-run (gate scores used) |

## Findings

Full list in `findings.jsonl` (2 items, both info — nothing actionable):

1. [info] PUT /books/{id} uses merge (partial-update) semantics, not full replace — `src/BookAPI.m:97-104`
2. [info] HTTP server handles one connection at a time — `src/HTTPServer.m:serveForever`

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json     # pinned 12-item checklist
grep -rE "skip|disabled|XCTSkip" tests/   # 0 skips
# To re-verify from scratch (not required): make test
```
