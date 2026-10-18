# Evaluation: agent=codex_effort=low_language=swift_model=gpt-6-luna_prompt=neutral · rep 3

## Summary

- **Factors:** language=swift, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (derived from `test_coverage=1.0` / `defect_rate=1.0`; not re-run)
- **Lint:** `code_quality=0.8333` (from `scores.json`)
- **Architecture:** summary skill not run; layout is `Book.swift` (model + validation), `BookStore.swift` (SQLite via `CSQLite` system library), `HTTPServer.swift` (hand-rolled HTTP/1.1 on Network.framework), `main.swift` (env-configured entrypoint)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `HTTPServer.swift:66-68` → `BookStore.create` (`BookStore.swift:27-39`); test `testCreateAndFetchBook` |
| R2 | GET /books lists all | ✓ implemented | `HTTPServer.swift:62-65`, `BookStore.all` (`BookStore.swift:41-50`) |
| R3 | ?author= filter | ✓ implemented | `HTTPServer.swift:63` parses + percent-decodes; `WHERE author = ?` at `BookStore.swift:43`; test `testAuthorFilter` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `HTTPServer.swift:71-73`; `BookStore.get` |
| R5 | PUT /books/{id} updates | ✓ implemented | `HTTPServer.swift:74-76`; `BookStore.update` (404 via `sqlite3_changes`); test `testUpdateAndDelete` |
| R6 | DELETE /books/{id} | ✓ implemented | `HTTPServer.swift:77-79` → 204; test `testUpdateAndDelete` |
| R7 | SQLite storage | ✓ implemented | `BookStore.swift:8-22` `sqlite3_open` + `CREATE TABLE`; `Package.swift` `.systemLibrary(CSQLite)` |
| R8 | JSON + proper status codes | ✓ implemented | `HTTPServer.swift:84-104` maps 200/201/204/400/404/500, `Content-Type: application/json` |
| R9 | title/author required → 400 | ✓ implemented | `Book.swift:32-41` rejects nil/blank; `ServiceError.badRequest` → 400 (`HTTPServer.swift:86`); test `testRequiredFieldsAreValidated` |
| R10 | GET /health | ✓ implemented | `HTTPServer.swift:61` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, `swift build`/`swift run`, env vars, API, `swift test` |
| R12 | ≥3 tests that run | ✓ implemented | 4 XCTest cases in `Tests/BookServiceTests/BookStoreTests.swift`; `test_coverage=1.0` |

Enhancements beyond spec: `PORT`/`DATABASE_PATH` env overrides, whitespace trimming of title/author, NSLock-serialised DB access.

## Build & Test

```text
not re-run (per skill step 2) — scores.json:
{"code_quality": 0.8333, "token_efficiency": 0.0179, "test_coverage": 1.0, "defect_rate": 1.0, "maintainability": 0.6579, "idiomatic": 0.55}
```

```text
grep -rnE "XCTSkip" Tests  → 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 303 |
| Lines of test code | 37 |
| Files | 5 Swift (4 source + 1 test) + modulemap/header |
| Dependencies | 0 external (system sqlite3 only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [medium] Out-of-range `year` crashes the server — `Int32(value)` traps at `BookStore.swift:125`
2. [low] Tests cover `BookStore` only; HTTP routing/status codes untested
3. [info] Unsupported methods on known routes return 404 instead of 405

## Reproduce

```bash
cd "<run_dir>"
cat scores.json
cat ../../../REQUIREMENTS.json
grep -rnE "XCTSkip" Tests | wc -l
wc -l Sources/BookService/*.swift Tests/*/*.swift
```
