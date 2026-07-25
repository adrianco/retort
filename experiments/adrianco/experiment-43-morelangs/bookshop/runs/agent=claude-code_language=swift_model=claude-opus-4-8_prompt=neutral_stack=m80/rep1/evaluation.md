# Evaluation: swift · claude-code · m80 · rep 1

## Summary

- **Factors:** language=swift, model=claude-opus-4-8, agent=claude-code, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective) — from `test_coverage=1.0` in `scores.json`
- **Build:** pass — `test_coverage=1.0` implies build + all tests succeeded (not re-run)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Router.swift:createBook` → `BookStore.create`; test `RouterTests.testCreateBookReturns201WithId` |
| R2 | GET /books lists all | ✓ implemented | `Router.swift:routeBooks` GET → `BookStore.all`; test `testListAndAuthorFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookStore.all(author:)` `WHERE author = ?`; tests `testListAndAuthorFilter`, `testAuthorFilterOverHTTP` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `Router.swift` item GET → `BookStore.get`, 404 branch; tests `testGetSingleBook`, `testGetMissingBookReturns404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Router.swift:updateBook` → `BookStore.update`; tests `testUpdateBook`, `testUpdateMissingBookReturns404` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Router.swift` DELETE → `BookStore.delete` (204); tests `testDeleteBook`, `testDeleteMissingBookReturns404` |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore.swift` uses `import SQLite3`, `sqlite3_open`, real `books` table |
| R8 | JSON + appropriate status codes | ✓ implemented | `HTTPResponse.json/error`; 201/200/204/400/404/405/500 across `Router.swift` |
| R9 | Validation: title & author required | ✓ implemented | `Book.swift:BookInput.validated()` throws on blank; tests `testCreateBookRequiresTitle`, `testCreateBookRequiresAuthor`, `testValidationOverHTTP` |
| R10 | GET /health | ✓ implemented | `Router.swift` health case returns `{status: ok}`; tests `testHealthCheck`, `testHealthEndpoint` |
| R11 | README with setup/run | ✓ implemented | `README.md` (4.2 KB) — requirements, layout, build/run/test instructions |
| R12 | ≥ 3 tests | ✓ implemented | 20 test functions across 3 files; `test_coverage=1.0` |

## Build & Test

Build and tests were **not re-run** — stored scores are authoritative per the skill:

```text
scores.json: test_coverage=1.0  → build + all tests passed
             code_quality=0.833 → lint/quality
             defect_rate=1.0    → build+test succeeded
             maintainability=0.594  idiomatic=0.65
```

```text
20 test functions (RouterTests 13, IntegrationTests 4, HTTPParsingTests 3)
0 skipped / disabled (grep for XCTSkip/disabled → 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 607 |
| Lines of code (tests) | 306 |
| Files (excl. .build/.git) | 19 |
| Dependencies (external) | 0 (system SQLite3 + Network) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `GET /books?author=` (empty value) filters by empty author instead of listing all — `Router.swift:44`
2. [info] Server uses `Connection: close` — one request per TCP connection — `HTTPServer.swift:90`
3. [info] Test suite requires full Xcode (XCTest); documented in README — tests passed here (`test_coverage=1.0`)

No critical/high/medium findings: all 12 requirements implemented, tests pass, no skips.

## Reproduce

```bash
cd experiments/adrianco/experiment-43-morelangs/bookshop/runs/agent=claude-code_language=swift_model=claude-opus-4-8_prompt=neutral_stack=m80/rep1
cat scores.json                              # stored build/test/lint scores (authoritative)
grep -rE "func test" Tests | wc -l           # 20 test functions
grep -rEn "XCTSkip|disabled|\.skip" Tests    # 0 skips
# Optional full rebuild (not required — scores.json is authoritative):
swift test
```
