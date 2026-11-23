# Evaluation: rest-api-crud · agent=codex effort=low language=swift model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral (framework=unknown)
- **Status:** ok (repair task — previous attempt repaired; build + all tests pass)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build succeeded)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

This was a REPAIR task: a prior attempt failed independent evaluation ("build/tests did not
fully pass"). The agent fixed the existing code in place. Stored mechanical scores confirm
the repair succeeded: `test_coverage=1.0` (build compiled and every test ran and passed) and
`defect_rate=1.0`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `Books.swift:119-126` decodes `Fields`, saves → 201; test `testLifecycle` (Tests.swift:19-21) |
| R2 | GET /books lists all books | ✓ implemented | `Books.swift:116-118` → `Database.list(nil)` (Books.swift:70-74); test `testPersistenceAndFilter` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `Books.swift:117` reads `author` query item → `list(author:)` WHERE clause (Books.swift:72); test asserts filtered rows (Tests.swift:43-47) |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `Books.swift:115` → `Database.get` throws `APIError(404)` (Books.swift:76-80); `testLifecycle` checks 404 after delete |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Books.swift:119,126` `("PUT",.some)` → `save(id:)` + `checkChanged` 404 (Books.swift:82-99); `testLifecycle` PUT asserts 200 + replacement |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Books.swift:127-129` → `Database.delete` (Books.swift:93-96); `testLifecycle` delete asserts 200 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `Database` uses libsqlite3 via CSQLite shim; schema at `Books.swift:42`; file-backed `books.sqlite3` + `:memory:` in tests |
| R8 | JSON responses + appropriate HTTP status codes | ✓ implemented | `JSONEncoder` throughout `route` (Books.swift:103-132); codes 200/201/400/404/405/413/500/501; `Content-Type: application/json` (Server.swift:64) |
| R9 | Input validation: title and author required | ✓ implemented | Trims then rejects blank title/author → 400 (Books.swift:123-125); `testValidation` covers 5 invalid payloads (Tests.swift:50-59) |
| R10 | GET /health endpoint | ✓ implemented | `Books.swift:106` returns 200 `{"status":"ok"}`; `testHealth` (Tests.swift:61-64) |
| R11 | README.md with setup + run instructions | ✓ implemented | `README.md` — install steps, `make build/test/run`, env vars, route table, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 test functions in `Tests.swift`; `test_coverage=1.0` confirms they ran and passed |

No prompt-factor requirements: `prompt=neutral` maps to the neutral instruction, which adds
no additional checkable asks beyond TASK.md.

## Build & Test

Build/test were **not re-run** — stored mechanical scores from `scores.json` are authoritative:

```text
scores.json
{"code_quality": 0.8333, "token_efficiency": 0.0380, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.5914, "idiomatic": 0.45}
```

- `test_coverage=1.0` ⇒ `swift build` compiled and all 5 tests executed and passed.
- `defect_rate=1.0` ⇒ build+test succeeded.
- No skipped/disabled tests found (`grep XCTSkip|.skip|DISABLED_` → 0).

Test commands (per Makefile, for reference): `swift build --disable-sandbox`,
`swift test --disable-sandbox`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 322 (Books.swift 132, Server.swift 107, Tests.swift 83) |
| Files (excl. .build/.git) | 18 |
| Dependencies (external SwiftPM packages) | 0 (system libsqlite3 only) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored inline) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] Zero external dependencies — hand-rolled HTTP/1.1 server over raw libsqlite3
2. [info] Persistence stores full record as a JSON document column plus denormalized author
3. [info] Server is synchronous, one request per connection (`Connection: close`)

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=swift_model=gpt-6.2-astra_prompt=neutral/rep1
cat scores.json                 # stored mechanical scores (build/test authoritative)
cat stack.json _meta.json       # factor levels + success flag
grep -rnE "XCTSkip|\.skip|DISABLED_" --include="*.swift" .   # skip detection → 0
wc -l Books.swift Server.swift Tests.swift                   # LOC
# To re-verify the toolchain (optional — scores already stored):
# swift test --disable-sandbox
```
