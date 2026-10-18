# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok — repair task; the previous attempt's failure (missing `wrap-params`) is fixed and verified
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.95` (scores.json)
- **Architecture:** run-summary skill unavailable in this session; see module notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

This is a REPAIR run. `FEEDBACK.md` reported the prior attempt failed because the
`?author=` filter never worked over HTTP — `wrap-params` middleware was missing. The
current code wires `wrap-params` into the handler (`src/book_api/core.clj:60-63`) and adds
a dedicated regression test that drives the full middleware stack via a raw
`:query-string` (`test/book_api/core_test.clj:45-54`). `test_coverage=1.0` confirms build +
all tests pass.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `core.clj:40-43` → `db/create-book!` `db.clj:57-70` |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:37-38` → `db/list-books` `db.clj:49-52` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.clj:51` LIKE filter; HTTP test `core_test.clj:45-54` (verifies wrap-params) |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `core.clj:48` → `db/get-book`; 404 at `core.clj:48` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `core.clj:50-53` → `db/update-book!` `db.clj:72-81` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `core.clj:54` → `db/delete-book!` `db.clj:83-87` |
| R7 | Data stored in SQLite | ✓ implemented | `org.xerial/sqlite-jdbc` dep; `db.clj:7-27` JDBC + CREATE TABLE |
| R8 | JSON responses + correct status codes | ✓ implemented | `wrap-json-response` `core.clj:63`; 201/200/204/400/404 throughout `core.clj` |
| R9 | Validation: title and author required | ✓ implemented | `valid-book?` `core.clj:9-14`; 400 at `core.clj:43`; test `core_test.clj:22,27` |
| R10 | GET /health | ✓ implemented | `core.clj:34-35`; test `core_test.clj:17-19` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — run, env vars, API, tests |
| R12 | >= 3 tests | ✓ implemented | 4 `deftest`s in `core_test.clj`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   → build succeeded and all tests passed
code_quality  = 0.95
defect_rate   = 0.787
maintainability = 0.920
idiomatic     = 0.35
```

Tests (`clojure -M:test` → `book-api.test-runner`): 4 deftests, 0 skips, 0 failures.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test .clj) | 217 |
| Files (excl .git) | 15 |
| Dependencies | 5 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Full list in `findings.jsonl`:

1. [low] R3 — `?author=` filter uses substring `LIKE %x%` match rather than exact match (`db.clj:51`). Acceptable for the spec.
2. [info] R8 — DELETE returns 204 No Content with nil body (`core.clj:54`). Correct REST semantics.

No critical, high, or medium findings. The run is a clean pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                      # test_coverage=1.0, code_quality=0.95
grep -c deftest test/book_api/core_test.clj   # 4
# optional, builds + runs tests (slow; scores already stored):
#   clojure -M:test
```
