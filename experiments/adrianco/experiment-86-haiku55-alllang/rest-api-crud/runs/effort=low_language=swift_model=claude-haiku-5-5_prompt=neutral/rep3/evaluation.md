# Evaluation: effort=low language=swift model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=swift, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Router.swift:94 createBook` → `BookStore.swift:33 create`; test `testCreateThenFetchBook` |
| R2 | GET /books lists all books | ✓ implemented | `Router.swift:89 listBooks` → `BookStore.swift:47 list`; test `testListFiltersByAuthorCaseInsensitively` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookStore.swift:49-50` `WHERE author = ? COLLATE NOCASE`; test asserts filtered titles (line 46-47) |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `Router.swift:107 getBook`; `testMissingBookReturnsNotFound` (404 + non-numeric id) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Router.swift:112 updateBook` → `BookStore.swift:56 update`; `testUpdateReplacesFields` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Router.swift:125 deleteBook` → `BookStore.swift:65 delete` (204); `testDeleteRemovesBook` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.swift:2 import SQLite3`, CREATE TABLE at :20; `Package.swift` links `sqlite3` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `Router.swift` 201/200/204/400/404/405, `HTTPResponse.json`; reason phrases `HTTPServer.swift:121` |
| R9 | Input validation: title and author required | ✓ implemented | `BookValidator.validate` (`Book.swift:44-62`); `testCreateRejectsMissingOrBlankRequiredFields` (400) |
| R10 | GET /health endpoint | ✓ implemented | `Router.swift:61-64`; `testHealthEndpointReportsOK` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — build/run/test, API table, validation, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 11 `func test*` in `BookAPITests.swift`; test_coverage=1.0 |

No requirements missing or partial. Enhancements beyond spec: chunk-safe HTTP
parser with `413`/`malformed` handling, `405` + `Allow` header, `Location`
header on create, trimming/normalization and plausible-year validation.

## Build & Test

Build and test were not re-run — stored scores are authoritative.

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
             maintainability=0.7010  idiomatic=0.42  token_efficiency=0.0439
test_coverage=1.0 ⇒ `swift test` built the package and all tests passed.
```

Skip scan: `grep XCTSkip/skip/disabled Tests/` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source + tests) | 622 |
| Files (excl. .git) | 16 |
| Dependencies | 0 third-party (system `libsqlite3`, Network.framework) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | not re-run (stored score) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Socket layer (`HTTPServer.start/serve/send`) not exercised end-to-end — tests drive `BookRouter.handle` directly and only `HTTPServer.parse` is unit-tested.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/quality scores
grep -rnE "XCTSkip|skip|disabled" Tests/          # skip scan (0)
grep -cE "func test" Tests/BookAPITests/BookAPITests.swift   # test count (11)
# build/test NOT re-run — test_coverage=1.0 is authoritative
```
