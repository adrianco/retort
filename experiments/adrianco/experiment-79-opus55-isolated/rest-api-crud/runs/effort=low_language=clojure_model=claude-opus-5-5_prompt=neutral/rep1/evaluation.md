# Evaluation: effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 deftest / 0 failed / 0 skipped (10 effective) — pass confirmed by `test_coverage=1.0` (scores.json)
- **Build:** pass — from `test_coverage=1.0`/`defect_rate=1.0` (scores.json; not re-run per skill)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/books/core.clj:93-95` → `db/create-book!` `src/books/db.clj:24-29` (INSERT ... RETURNING *) |
| R2 | GET /books lists all books | ✓ implemented | `src/books/core.clj:89-91` → `db/list-books` `src/books/db.clj:31-39` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/books/core.clj:90` passes author; `db.clj:36-37` WHERE author = ? |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/books/core.clj:97-101` (404 branch); `db/get-book` `db.clj:41-42` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/books/core.clj:103-109` → `db/update-book!` `db.clj:44-51` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/books/core.clj:111-115` → `db/delete-book!` `db.clj:53-57` (204/404) |
| R7 | Data stored in SQLite | ✓ implemented | `src/books/db.clj:8-22` next.jdbc `:dbtype "sqlite"`, CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `core.clj:12-20` respond/error helpers; 201/200/204/400/404/500 across routes |
| R9 | Input validation: title & author required | ✓ implemented | `core.clj:33-47` validate (blank-string rejected); `with-valid-book` → 400 with details |
| R10 | GET /health endpoint | ✓ implemented | `src/books/core.clj:87` returns 200 `{status:"ok"}` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Requirements/Run/Test/API sections + curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/books/core_test.clj` — 10 deftests; `test_coverage=1.0` |

No requirements partial or missing. Two info-level enhancements beyond spec are noted in `findings.jsonl`.

## Build & Test

Per the evaluate-run skill, build/test/lint were **not re-run** — stored scores from `scores.json` stand in:

```text
scores.json
test_coverage = 1.0   -> build succeeded and all tests passed
defect_rate   = 1.0   -> build+test succeeded
code_quality  = 1.0   -> lint/quality clean
maintainability = 0.933
idiomatic       = 0.88
token_efficiency = 0.038
```

Test suite (static inspection): 10 `deftest` blocks in `test/books/core_test.clj`
covering health, create+get, optional fields, validation (missing title/author,
blank + wrong types, malformed/non-object JSON), list+author-filter, update
(incl. invalid + unknown id), content-type-independent body, delete, not-found.
Skip/disabled scan: 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 292 (core 126, db 57, test 109) |
| Files | 13 (incl. logs/config); 3 source `.clj` |
| Dependencies | 8 runtime (deps.edn) + 2 test |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Validation exceeds spec: year/isbn type checks and non-object-body rejection
2. [info] Content-Type-independent body parsing and regex-guarded ids

No correctness, build, test, or requirement findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                       # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json        # pinned requirement checklist
grep -rc deftest test/                # test count
# Optional live run:
#   clojure -M:test                   # runs the integration suite
#   clojure -M:run                    # starts the server on :3000
```
