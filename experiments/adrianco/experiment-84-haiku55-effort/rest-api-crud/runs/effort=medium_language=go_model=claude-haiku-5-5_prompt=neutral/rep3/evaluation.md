# Evaluation: effort=medium language=go model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate output): `test_coverage=0.801`, `defect_rate=1.0`, `code_quality=1.0`, `maintainability=0.910`, `idiomatic=0.88`. Build/tests were **not** re-run — `defect_rate=1.0` confirms the toolchain built and the full suite passed; `test_coverage=0.801` is the coverage fraction (> 0, so the test gate passed).

The `prompt=neutral` factor file (`prompts/neutral.md`) prescribes no methodology and adds no checkable requirement, so the pinned 12-item `REQUIREMENTS.json` is the complete spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:53 createBook` → `store.go:62 Create`; `api_test.go:53 TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:67 listBooks` → `store.go:93 List`; `api_test.go:127` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `handlers.go:68` reads `author`; `store.go:96 WHERE author = ? COLLATE NOCASE`; `api_test.go:141` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `handlers.go:77 getBook`; `store.go:82 ErrNotFound`→404; `api_test.go:206` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:90 updateBook` → `store.go:124 Update`; `api_test.go:160 TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:107 deleteBook` → `store.go:138 Delete`; `api_test.go:191 TestDeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:10 modernc.org/sqlite`, `store.go:20 schema`; `api_test.go:236 TestDataPersistsAcrossRestart` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `handlers.go:170 writeJSON`; 201/200/204/400/404/409/405 across handlers; `api_test.go:218` |
| R9 | Validation: title and author required | ✓ implemented | `book.go:44 validate` (title/author required); `api_test.go:79 TestCreateValidation` |
| R10 | GET /health health check | ✓ implemented | `handlers.go:44 health` (pings DB); `api_test.go:209 TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup / Run / Test sections, env vars |
| R12 | At least 3 unit/integration tests | ✓ implemented | 17 test functions in 3 files; `test_coverage=0.801` > 0 |

No requirement is partial or missing. Beyond-spec extras (ISBN checksum validation, ISBN uniqueness/409, JSON 405 + `Allow`, 1 MiB body cap, graceful shutdown) are recorded as `info` enhancements, not deductions.

## Build & Test

Build and tests were not re-run per the skill (stored scores authoritative).

```text
scores.json (inline gate output)
defect_rate   = 1.0    # build + full test suite succeeded
test_coverage = 0.801  # coverage fraction (> 0 → test gate passed)
code_quality  = 1.0
```

```text
Test functions (17, 0 skipped):
  api_test.go   — 11 (create/get, validation, malformed JSON, duplicate ISBN,
                       list+author filter, update, update-404, delete, bad IDs,
                       health, 405/unknown routes, persist-across-restart)
  store_test.go — 3  (not-found errors, empty-ISBN coexistence, update-to-taken ISBN)
  book_test.go  — 3  (ISBN validation, normalize, year bounds)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test .go) | 512 |
| Lines of code (test .go) | 391 |
| Source files (.go) | 7 |
| Dependencies (go.sum lines) | 50 |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build | pass (`defect_rate=1.0`) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] ISBN-10/13 checksum validation beyond spec (`book.go:64`)
2. [info] ISBN normalization and uniqueness → 409 Conflict (`store.go:17`, `handlers.go:124`)
3. [info] JSON 405 with `Allow` header and 1 MiB body cap (`handlers.go:31`, `handlers.go:15`)
4. [info] Graceful shutdown + configurable ADDR/DB_PATH (`main.go:37`, `main.go:15`)

No critical/high/medium/low findings — a clean, fully-conformant run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/quality scores
grep -rhE "^func Test" *_test.go | wc -l          # 17 test functions
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l book.go store.go handlers.go main.go        # source LOC
# (optional, not required) full verification:
#   go test ./...
```
