# Evaluation: effort=low language=clojure model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 deftests, all passing / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `core.clj:50-51` POST route → `db/create-book!` (`db.clj:24-27`) |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:47-49` → `db/list-books` (`db.clj:16-19`) |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:48` reads query-param; `db.clj:17-18` WHERE author=?; test `author-filter` core_test.clj:52-58 |
| R4 | GET /books/{id} single book | ✓ implemented | `core.clj:52-55` → `db/get-book`; 404 branch present |
| R5 | PUT /books/{id} updates | ✓ implemented | `core.clj:56-61` → `db/update-book!` (full replacement, `db.clj:29-31`); test crud-flow:32-34 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `core.clj:62-65` → `db/delete-book!` (`db.clj:33-34`); 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `db.clj:8-14` next.jdbc SQLite datasource + CREATE TABLE; sqlite-jdbc dep in deps.edn |
| R8 | JSON + appropriate status codes | ✓ implemented | `json-resp` (`core.clj:11-14`); codes 200/201/204/400/404 across routes |
| R9 | Validation: title & author required | ✓ implemented | `validate` core.clj:21-29; test `validation` core_test.clj:40-50 asserts 2 errors |
| R10 | GET /health | ✓ implemented | `core.clj:46`; test `health` core_test.clj:20-23 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `clojure -M:run` / `-M:test`, env vars, endpoints |
| R12 | ≥3 tests | ✓ implemented | 4 deftests in `test/books/core_test.clj`; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 1.0   # build + all tests passed
code_quality  = 1.0   # lint/quality
defect_rate   = 1.0   # build+test succeeded
maintainability = 0.956
idiomatic       = 0.72
```

Skip scan (core_test.clj): 0 skipped / disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + test) | 164 |
| Files (source) | 3 |
| Dependencies | 9 (7 runtime + 2 test) |
| Tests total | 4 deftests |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [info] Validation exceeds spec — type-checks year/isbn and rejects malformed JSON (`core.clj:16-29`)

No critical/high/medium/low findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build/test/lint)
grep -rcE "\(deftest" test/     # test count
clojure -M:test                 # (optional) re-run tests
```
