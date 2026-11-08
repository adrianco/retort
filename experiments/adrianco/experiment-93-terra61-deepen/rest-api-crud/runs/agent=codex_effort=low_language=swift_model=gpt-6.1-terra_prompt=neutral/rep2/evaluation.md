# Evaluation: agent=codex effort=low language=swift model=gpt-6.1-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=swift, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 test methods passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` and `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** run-summary skill not available in this session; module overview inlined below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean run. A library target (`BooksCore`) holds the SQLite-backed store and a
transport-agnostic `BookAPI` router; a thin `BooksServer` executable wraps it in a
raw-socket HTTP/1.1 server. Tests target the library directly, so all CRUD paths are
exercised without standing up a socket.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Sources/BooksCore/BooksCore.swift:112-114` POST → `store.create`, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `BooksCore.swift:111` GET → `store.list(...)`; `BookStore.list` :55-62 |
| R3 | GET /books ?author= filter | ✓ implemented | `BooksCore.swift:111` reads `author` query item; `list` :57 `WHERE author = ?` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `BooksCore.swift:120` → `store.get`, 404 on nil; test asserts 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BooksCore.swift:121-123`; `BookStore.update` :79-85 (404 if no row) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BooksCore.swift:124`; `BookStore.delete` :86-91 |
| R7 | SQLite / embedded DB | ✓ implemented | `CSQLite` system library; `BookStore` uses `sqlite3_*`, real file path in server :64 |
| R8 | JSON responses + status codes | ✓ implemented | `response()`/`error()` :101-102 encode JSON; 201/200/400/404/405/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `validInput` :129-130 rejects empty/whitespace title or author → 400; test :25-26 |
| R10 | GET /health | ✓ implemented | `BooksCore.swift:107` returns 200 `{"status":"ok"}`; test :37-39 |
| R11 | README with setup & run | ✓ implemented | `README.md` — build/run, env vars, full API + curl examples |
| R12 | ≥ 3 tests | ✓ implemented | 3 XCTest methods in `BooksCoreTests.swift`; `test_coverage=1.0` |

No requirement is partial or missing.

## Build & Test

Build/test were **not re-run** — stored mechanical scores stand in (per skill step 2):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
→ build succeeded, all tests executed and passed, lint clean
```

Tests (`Tests/BooksCoreTests/BooksCoreTests.swift`), run against the in-process
`BookAPI`/`BookStore`:

```text
testCRUDAndFiltering        — create→filter→get→update→delete→404 round trip
testValidationAndMissingResources — 400 on empty/missing fields, 404 on missing id, 405 on bad method
testPersistenceAndHealth    — data survives store reopen (on-disk SQLite), /health = 200
```

Skip scan (`XCTSkip`/disabled): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source + tests) | 257 |
| Files (Sources + Tests) | 5 |
| SPM targets | 4 (CSQLite system lib, BooksCore, BooksServer, BooksCoreTests) |
| Third-party Swift deps | 0 (system SQLite only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| token_efficiency | 0.0175 (from scores.json) |

## Findings

Full list in `findings.jsonl`. Both are info-level (beyond-spec notes, not defects):

1. [info] Server handles connections serially — single-threaded accept loop (`main.swift:76-82`)
2. [info] `?author=` filter is exact / case-sensitive (`BooksCore.swift:57`, documented in README)

No critical/high/medium/low findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=swift_model=gpt-6.1-terra_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json                     # pinned 12-requirement checklist
grep -rnE "XCTSkip|disabled" Tests/                # skip scan → 0
wc -l $(find Sources Tests -name '*.swift')        # LOC
# Optional full re-run: swift build && swift test
```
