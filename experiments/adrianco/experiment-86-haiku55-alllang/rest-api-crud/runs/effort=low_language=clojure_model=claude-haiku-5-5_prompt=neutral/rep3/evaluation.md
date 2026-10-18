# Evaluation: effort=low language=clojure model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=clojure, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests ran)
- **Lint:** pass — code_quality=0.9667 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handler.clj:36 create` → `db.clj:30 create-book!` (201); test `api_test.clj:43` |
| R2 | GET /books lists all books | ✓ implemented | `handler.clj:42 list-all` → `db.clj:19 list-books`; test `api_test.clj:58` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.clj:22-24` WHERE author=? on query-param; test `api_test.clj:64` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `handler.clj:45 get-one` → not-found; test `api_test.clj:82-84` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handler.clj:50 update-one` → `db.clj:37 update-book!`; test `api_test.clj:67` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handler.clj:58 delete-one` → `db.clj:47 delete-book!` (204); test `api_test.clj:76` |
| R7 | Data stored in SQLite | ✓ implemented | `db.clj:10` jdbc:sqlite + `deps.edn` org.xerial/sqlite-jdbc |
| R8 | JSON responses + status codes | ✓ implemented | `handler.clj:90 app` wrap-json-response; 201/200/204/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `handler.clj:10 validate`; tests `validation_test.clj:9`, `api_test.clj:52` |
| R10 | GET /health | ✓ implemented | `handler.clj:70-71` returns {status "ok"}; test `api_test.clj:38` |
| R11 | README with setup/run | ✓ implemented | `README.md` — run, test, env vars, API table, curl examples |
| R12 | ≥3 tests | ✓ implemented | 12 deftests across 2 files; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (inline gate output) — build/test/lint not re-run per skill policy:

```text
test_coverage   = 1.0     (build + all tests executed and passed)
code_quality    = 0.9667
defect_rate     = 0.9123
maintainability = 0.9417
idiomatic       = 0.6
token_efficiency= 0.0210
```

Test runner: `clojure -M:test` → `books.test-runner/-main` runs `books.api-test` + `books.validation-test`, exits non-zero on any failure/error.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 269 |
| Files (excl. .git) | 16 |
| Dependencies (deps.edn) | 7 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] PUT replaces all fields (full-replace semantics) — omitted year/isbn become NULL (`db.clj:42`)
2. [info] ?author= filter is exact-match only (`db.clj:23`)
3. [info] GET /books returns the full collection unpaginated (`handler.clj:42`)

None are spec violations; all requirements are satisfied.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json              # stored build/test/lint scores (not re-run)
cat ../../REQUIREMENTS.json  # pinned 12-requirement checklist
grep -rcE "deftest" test/    # test count
# Optional full run: clojure -M:test
```
