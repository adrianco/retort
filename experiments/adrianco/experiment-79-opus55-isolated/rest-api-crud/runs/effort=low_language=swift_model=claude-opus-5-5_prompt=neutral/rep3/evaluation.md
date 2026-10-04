# Evaluation: rest-api-crud · effort=low language=swift model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=swift, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — from `test_coverage=1.0` (build + all tests executed; not re-run)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Router.swift:36` → `BookStore.create` (`BookStore.swift:37`); tested `testCreateAndGet:30` |
| R2 | GET /books lists all | ✓ implemented | `Router.swift:33` → `store.list`; `testListAndAuthorFilter:72` |
| R3 | GET /books ?author= filter | ✓ implemented | `Router.swift:34` `request.query["author"]` → `BookStore.list` `WHERE author = ? COLLATE NOCASE` (`BookStore.swift:50`); `testListAndAuthorFilter:81` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `Router.swift:56`; 404 at `:57`; `testNotFoundAndMethodNotAllowed:113` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Router.swift:59` → `BookStore.update`; `testUpdate:87` |
| R6 | DELETE /books/{id} | ✓ implemented | `Router.swift:64` → `BookStore.delete`, 204; `testDelete:102` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.swift` uses `SQLite3`; persistence tested `testDataPersistsAcrossReopen:127` |
| R8 | JSON + appropriate status codes | ✓ implemented | `HTTP.swift:79` `json`/`error`; codes 200/201/204/400/404/405/413/422/500 |
| R9 | Validation: title & author required | ✓ implemented | `BookInput.parse` (`Book.swift:57-72`); rejects blank/whitespace/non-string; `testCreateValidation:54`. Returns 422 (spec example says 400 — info finding) |
| R10 | GET /health | ✓ implemented | `Router.swift:24` → `{"status":"ok"}`; `testHealth:23` |
| R11 | README with setup/run | ✓ implemented | `README.md` (run, env vars, test instructions) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 test functions across 4 XCTestCase classes; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill Step 2):

```text
test_coverage    = 1.0    → build succeeded + all tests passed
defect_rate      = 1.0    → build+test succeeded
code_quality     = 0.833  → lint/quality
maintainability  = 0.839
idiomatic        = 0.78
token_efficiency = 0.098
```

Test suite (`Tests/BookAPITests/BookAPITests.swift`): 13 `func test…` across `RouterTests`, `StoreTests`, `HTTPParsingTests`, `ServerIntegrationTests` (real socket end-to-end). No `XCTSkip` / skipped tests found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source + tests) | 726 |
| Files (excl. .git/.build) | 17 |
| Dependencies | 0 third-party (system `sqlite3` + Network.framework only) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores cached) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `low`:

1. [info] R9 validation returns 422 where the spec example cites 400 (malformed bodies do return 400). 422 is a defensible choice; R9 is satisfied.
2. [info] Robustness beyond spec: parameterized SQL (SQLi-tested), 1 MB body-size limit → 413, `NSLock` thread safety, `Location`/`Allow` headers.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=swift_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                       # cached build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json        # pinned R1–R12 checklist
grep -rcE 'func test' Tests/BookAPITests/BookAPITests.swift   # 13
grep -rnE 'XCTSkip' Tests/            # none
# Optional full verify: swift test   (toolchain: swift 5.9+, macOS 13+)
```
