# Evaluation: agent=codex effort=low language=swift model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (implied by `test_coverage=1.0`; `swift test` builds too)
- **Lint:** pass — `code_quality=0.8333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Scores read from `scores.json` (inline-gate archive; `retort.db` row not yet queryable):
`test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.833`, `maintainability=0.717`, `idiomatic=0.72`, `token_efficiency=0.032`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookAPI.swift:46-49` → `BookStore.create` `BookStore.swift:117`; returns 201 + `Location` |
| R2 | GET /books lists all books | ✓ implemented | `BookAPI.swift:43-45` → `BookStore.list` `BookStore.swift:125` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookAPI.swift:44` reads `author` query item; `BookStore.swift:126` adds `WHERE author = ?`; test `BookAPITests.swift:58` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `BookAPI.swift:61-63` → `store.get`; 404 via `missingBook` `:79` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookAPI.swift:64-67` → `BookStore.update` `:142`; 404 when no row changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookAPI.swift:68-69` → `BookStore.delete` `:151`; returns 204, 404 if absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `BookStore.swift:31-50` opens sqlite3 + `CREATE TABLE books`; `CSQLite` system library target |
| R8 | JSON responses + appropriate HTTP codes | ✓ implemented | `Response.json` `:8`; 201/200/204/400/404/405 across `BookAPI.swift`; `HTTPServer.swift:134-152` maps reason phrases + Content-Type |
| R9 | Validation: title and author required | ✓ implemented | `BookInput.isValid` `BookStore.swift:10-13` (rejects blank); `decode` → 400 `BookAPI.swift:85-90`; test `:67-81` |
| R10 | GET /health endpoint | ✓ implemented | `BookAPI.swift:39-40` returns `{"status":"ok"}`; test `:94` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — build/test/run commands, env vars, endpoint table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 `func test*` in `BookAPITests.swift`; `test_coverage=1.0` |

## Build & Test

Not re-run — scores read from `scores.json` per the evaluate-run skill (compiled Swift; re-running duplicates the slowest step).

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.833
# test_coverage=1.0 ⇒ `swift build` + `swift test` succeeded, all tests passed.
```

```text
grep "func test" Tests/BookAPITests/BookAPITests.swift → 4 tests
skip scan (XCTSkip|disabled|XCTExpectFailure) → none
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Sources only) | 442 |
| Lines of code (tests) | 102 |
| Files (Sources + Tests) | 7 |
| Dependencies (external) | 0 (stdlib + system SQLite + Network only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Hardening beyond spec: parameterized queries (SQL-injection safe, asserted by a test), HTTP header/body size limits, and a 15s connection timeout.

No requirement, build, test, or skip findings — the run fully conforms to the spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=swift_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                                              # stored mechanical scores
cat ../../REQUIREMENTS.json                                  # pinned 12-item checklist
grep -c "func test" Tests/BookAPITests/BookAPITests.swift    # test count
grep -rnE "XCTSkip|disabled|XCTExpectFailure" Tests/         # skip scan (none)
# Optional full re-run: swift test
```
