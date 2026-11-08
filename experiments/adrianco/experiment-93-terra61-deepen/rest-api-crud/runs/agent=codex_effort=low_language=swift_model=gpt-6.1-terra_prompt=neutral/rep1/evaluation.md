# Evaluation: agent=codex effort=low language=swift model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.8333` (scores.json)
- **Architecture:** `BookService` library (SQLite-backed `BookStore` + routing `API`) consumed by a `BookServer` executable that implements a minimal from-scratch HTTP/1.1 server over POSIX sockets. Tests target the library's `API` directly.
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Sources/BookService/BookService.swift:128` POST → `store.create`, status 201; `create` at :81 |
| R2 | GET /books lists all books | ✓ implemented | `BookService.swift:127` GET → `store.list`; `list` at :56 |
| R3 | GET /books ?author= filter | ✓ implemented | `BookService.swift:127` reads `author` query item; `list(author:)` WHERE clause :58 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `BookService.swift:137-139`; `store.get` at :69, returns nil → 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookService.swift:140-143`; `update` at :89, 404 when no row changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookService.swift:144-146`; `delete` at :97, 404 when no row changed |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore` wraps CSQLite `sqlite3_*`; table DDL at `BookService.swift:34` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `JSONEncoder` at :113; 201/200/404/400/405/500 used throughout `handle` :117-149 |
| R9 | Validation: title and author required | ✓ implemented | `validInput` at `BookService.swift:151` rejects empty/whitespace title or author → 400 |
| R10 | GET /health health check | ✓ implemented | `BookService.swift:121-124` returns `{"status":"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup/run, env vars, API table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `func test*` in `Tests/BookServiceTests/BookServiceTests.swift`; `test_coverage=1.0` |

No requirement is partial or missing; no out-of-spec enhancement worth deducting.

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0    => build succeeded and all tests passed
code_quality  = 0.8333
defect_rate   = 1.0    => build+test succeeded
maintainability = 0.6656
idiomatic     = 0.42
```

Tests (`swift test`): `testCRUDAndFiltering`, `testValidationAndMissingRoutes`,
`testHealthAndPersistence` — exercise full CRUD, author filter, validation (400),
missing routes (404), method-not-allowed (405), health, and on-disk persistence.
0 skips (`grep` for `XCTSkip`/`skip`/`#[ignore]` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. tests) | 296 |
| Source files (.swift) | 3 |
| Files (excl. .git) | 15 |
| Dependencies (third-party Swift) | 0 (system SQLite only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

None. All 12 pinned requirements implemented and verified; build+tests pass; no
skipped tests; no correctness, security, or lint findings at or above `info`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=swift_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json                    # pinned 12-item checklist
grep -rE "XCTSkip|skip|#\[ignore\]" Tests         # skip detection (0)
grep -rE "func test" Tests --include="*.swift"    # 3 tests
# full build/test (optional, slow): swift test
```
