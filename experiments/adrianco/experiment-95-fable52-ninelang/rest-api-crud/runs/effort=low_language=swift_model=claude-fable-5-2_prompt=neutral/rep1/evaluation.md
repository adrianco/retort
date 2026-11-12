# Evaluation: rest-api-crud · effort=low language=swift model=claude-fable-5-2 prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 test methods / 0 failed / 0 skipped (12 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests passed) — not re-run
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** clean layering — `HTTP` (parser/req/resp) → `Router` (pure request→response) → `BookStore` (SQLite repo); `HTTPServer` + `main` wire the socket.
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Router.swift:36-37` → `BookStore.create` (`BookStore.swift:39`) |
| R2 | GET /books lists all | ✓ implemented | `Router.swift:33-35` → `store.list` (`BookStore.swift:51`) |
| R3 | GET /books ?author= filter | ✓ implemented | `Router.swift:34`; SQL `WHERE author = ? COLLATE NOCASE` (`BookStore.swift:54`); test `testListAndAuthorFilter` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `Router.swift:49-51` returns `missing` 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `Router.swift:52-56` → `store.update` (`BookStore.swift:83`) |
| R6 | DELETE /books/{id} | ✓ implemented | `Router.swift:57-58` → `store.delete`, 204/404; `testDelete` |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore.swift` uses `import SQLite3`, real table + on-disk path; `testDataSurvivesReopen` |
| R8 | JSON responses + status codes | ✓ implemented | `HTTP.swift:44` `json()`; codes 201/200/204/400/404/405/500 across Router |
| R9 | Validation: title & author required | ✓ implemented | `Book.swift:43-89` `BookInput.parse` → 400 with details; `testValidation` |
| R10 | GET /health | ✓ implemented | `Router.swift:22-25` returns `{"status":"ok"}`; `testHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/Test/API/env-var sections |
| R12 | ≥3 tests | ✓ implemented | 12 test methods across 4 XCTestCase classes; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill policy.

```text
scores.json: test_coverage=1.0  (build + all tests passed)
             code_quality=0.833  defect_rate=1.0  maintainability=0.806  idiomatic=0.82
```

Test inventory (grepped, no skip markers found):

```text
RouterTests:            testHealth, testCreateAndGet, testOptionalFieldsAreNull,
                        testValidation, testListAndAuthorFilter, testUpdate,
                        testDelete, testErrorRoutes
ParserTests:            testParsesCompleteRequest, testIncompleteAndInvalid
PersistenceTests:       testDataSurvivesReopen
ServerIntegrationTests: testFullLifecycleOverHTTP   (real TCP socket, async)
= 12 methods, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 786 |
| Source files | 6 Swift (Sources) + 1 (Tests) |
| Dependencies | 0 third-party (system `sqlite3` + Apple `Network`) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |

## Findings

No correctness, requirement, build, or test issues. Two info-level notes only:

1. [info] Server is macOS-only (Apple Network framework) — not required by the spec; core logic is portable.
2. [info] Robust beyond spec: body/header size limits (413/431), transfer-encoding rejection (501), 405 `Allow` headers.

## Reproduce

```bash
cd "experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=swift_model=claude-fable-5-2_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build+test not re-run)
grep -cE "func test" Tests/BookAPITests/BookAPITests.swift   # 12
grep -rEn "XCTSkip|\.skip" Tests/ | wc -l                    # 0
# optional: swift test   (macOS 12+, Swift 5.9+)
```
