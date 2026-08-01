# Evaluation: bookshop · language=swift model=gpt-5.6-terra agent=codex · rep 1

## Summary

- **Factors:** language=swift, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests ran green)
- **Lint:** pass — `code_quality=0.833` from `scores.json`; no lint findings surfaced
- **Architecture:** SwiftPM package: `BookCollection` library (SQLite-backed `BookStore` + routing `BookAPI`), `BookAPIServer` executable (raw BSD-socket HTTP loop), `BookCollectionTests` test target
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `BookCollection.swift:47 create`, routed `:147`; test `testCreateAndGetBook` |
| R2 | GET /books list | ✓ implemented | `BookCollection.swift:57 list`, routed `:150` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookCollection.swift:61` WHERE author=?; route parses query `:149`; test `testAuthorFilterAndUpdate` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `BookCollection.swift:68 get`, route `:157` → 404 on nil |
| R5 | PUT /books/{id} update | ✓ implemented | `BookCollection.swift:76 update` (404 on 0 changes), route `:158` |
| R6 | DELETE /books/{id} | ✓ implemented | `BookCollection.swift:88 delete`, route `:159` → 204/404; test `testValidationAndDelete` |
| R7 | SQLite / embedded DB | ✓ implemented | `import SQLite3`; `BookStore` uses `sqlite3_open`/prepared statements `:30-118` |
| R8 | JSON + appropriate status codes | ✓ implemented | `json()`/`error()` `:165-166`; status mapping `:175` (400/404/500), 201/204 in routes |
| R9 | Validation: title & author required | ✓ implemented | `validated()` `:97-103` throws `.validation` → 400; test `testValidationAndDelete` asserts 400 |
| R10 | GET /health | ✓ implemented | `BookCollection.swift:144`; test `testHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/API/Test sections, env var, ports |
| R12 | ≥3 tests | ✓ implemented | 4 `func test*` in `BookCollectionTests.swift`; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate):

```text
test_coverage = 1.0   → swift build + swift test succeeded, all tests green
defect_rate   = 1.0   → build+test success
code_quality  = 0.833
```

Test suite (`Tests/BookCollectionTests/BookCollectionTests.swift`) exercises the
`BookAPI` handler directly against an in-memory SQLite store (`:memory:`), covering
create/get, author-filter/update, validation/delete, and health.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 279 (233 lib+server, 46 tests) |
| Files (Sources+Tests) | 3 |
| Dependencies | 0 external (Foundation + system SQLite3 only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| test_coverage | 1.0 |

## Findings

None. All 12 pinned requirements implemented, all tests green, no skipped/disabled
tests. The implementation is idiomatic Swift (prepared statements guard against SQL
injection, `Result`-based routing, `NSLock` guarding the connection) with a
dependency-free raw-socket HTTP server. `idiomatic=0.45` is the only middling score;
it reflects the choice of a hand-rolled socket server over a framework like Vapor, not
a correctness defect.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=swift_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json          # mechanical scores (build/test already run by the gate)
swift build && swift test # re-run toolchain if desired
```
