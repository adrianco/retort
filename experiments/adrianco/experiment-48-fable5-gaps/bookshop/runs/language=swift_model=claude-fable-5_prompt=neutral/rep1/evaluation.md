# Evaluation: language=swift_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (test_coverage=1.0 implies build succeeded; not re-run)
- **Lint:** n/a — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookController.swift:16` create → `BookRepository.swift:59` INSERT; 201 |
| R2 | GET /books lists all | ✓ implemented | `BookController.swift:24` list → `BookRepository.swift:70` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookController.swift:25` reads `author` param → `BookRepository.swift:73` WHERE author COLLATE NOCASE |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `BookController.swift:29-35` → `HTTPError(.notFound)` when nil |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookController.swift:37` → `BookRepository.swift:103` UPDATE, 404 on no rows |
| R6 | DELETE /books/{id} | ✓ implemented | `BookController.swift:49` → `BookRepository.swift:117` DELETE; 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.swift:2` `import SQLite3`; real CREATE TABLE/INSERT |
| R8 | JSON + correct status codes | ✓ implemented | 201 (`:21`), 200, 404, 400, 204 (`:54`); Codable models |
| R9 | Validation: title+author required | ✓ implemented | `Models.swift:30-38` `validated()` throws 400 on missing/blank |
| R10 | GET /health | ✓ implemented | `Application+build.swift:16-19` pings DB, returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` (5 KB) — build/run, env vars, endpoint table |
| R12 | ≥ 3 tests | ✓ implemented | 7 `@Test` cases in `BookAPITests.swift`; `test_coverage=1.0` |

## Build & Test

Not re-run — per skill, stored scores stand in:

```text
scores.json: {"test_coverage": 1.0, "defect_rate": 1.0, "code_quality": 0.8333,
              "maintainability": 0.9146, "idiomatic": 0.62, "token_efficiency": 0.0059}
```

`test_coverage=1.0` ⇒ `swift build` + `swift test` passed and all 7 tests ran.
Skip scan (`.disabled(`, `XCTSkip`, `@Test(.enabled: false)`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source+tests) | 534 |
| Files (excl. .build/.git) | 18 |
| Dependencies | 1 (hummingbird) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; this is a clean run:

1. [info] Parameterized SQL throughout — no injection surface
2. [info] Actor-isolated single SQLite connection for thread safety
3. [info] Error coverage beyond spec (400 on bad id / malformed JSON, idempotent delete)
4. [info] Case-insensitive author filter

No requirement, build, test, or skipped-test findings.

## Reproduce

```bash
cd "runs/language=swift_model=claude-fable-5_prompt=neutral/rep1"
cat scores.json                        # stored build/test/quality scores
grep -rE "@Test" Tests/ --include="*.swift" | wc -l   # 7
# full toolchain (optional): swift build && swift test
```
