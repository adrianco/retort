# Evaluation: effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=swift, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ build + all tests passed (not re-run)
- **Lint:** n/a — `code_quality=0.833` from `scores.json`
- **Architecture:** `summary/index.md` not generated (run-summary skill unavailable in this session)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Sources/BookAPICore/App.swift:44-48`, `BookStore.swift:41-47` |
| R2 | GET /books lists all | ✓ implemented | `App.swift:50-54`, `BookStore.swift:50-63` |
| R3 | GET /books ?author= filter | ✓ implemented | `App.swift:51`, `BookStore.swift:52,56`; test `listWithAuthorFilter` `BookAPITests.swift:120` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `App.swift:56-60`, `find` `BookStore.swift:65`, `notFound` `App.swift:81` |
| R5 | PUT /books/{id} updates | ✓ implemented | `App.swift:62-67`, `update` `BookStore.swift:73-81` |
| R6 | DELETE /books/{id} | ✓ implemented | `App.swift:69-73`, `delete` `BookStore.swift:84-90` (204) |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore.swift` uses `CSQLite`; CREATE TABLE `BookStore.swift:26-34` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonResponse` `App.swift:99-106`; 201/200/404/204/400 across routes |
| R9 | title & author required (400) | ✓ implemented | `Book.swift:43-67`; test `rejectsMissingTitleAndAuthor` `BookAPITests.swift:27` |
| R10 | GET /health | ✓ implemented | `App.swift:33-40` (DB ping, 200/503) |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, test, API, env vars |
| R12 | ≥3 tests | ✓ implemented | 9 `@Test` functions, `test_coverage=1.0` |

## Build & Test

Build and tests were **not re-run** — scores read from `scores.json`:

```text
test_coverage = 1.0   ⇒ swift build + swift test passed, all tests executed
defect_rate   = 1.0   ⇒ build + test succeeded
code_quality  = 0.8333
maintainability = 0.8510
idiomatic     = 0.82
```

Skip scan: `grep -rE '\.disabled|XCTSkip' Tests/` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source + tests) | 515 |
| Files (Sources + Tests) | 7 |
| Package dependencies | 1 (Hummingbird) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [info] Validation goes beyond spec (ISBN-10/13 shape + year range) — enhancement, not a deduction.

No requirement gaps, build failures, test failures, or skipped tests.

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/quality scores
grep -rE '\.disabled|XCTSkip' Tests/              # skip scan (0)
grep -rc '@Test' Tests/                           # test count
find Sources Tests -name '*.swift' | xargs wc -l  # LOC
# build/test NOT re-run — test_coverage=1.0 already proves build+tests pass
```
