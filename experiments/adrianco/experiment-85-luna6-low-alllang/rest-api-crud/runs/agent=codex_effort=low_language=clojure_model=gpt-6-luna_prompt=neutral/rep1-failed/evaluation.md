# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (build + all tests pass; one requirement broken over HTTP)
- **Requirements:** 11/12 implemented, 1 partial (R3), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (not re-run)
- **Lint:** pass — code_quality=0.95 from scores.json
- **Architecture:** single Ring handler (core.clj) + JDBC/SQLite persistence layer (db.clj)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 1 high)

## Second-opinion verdict

This is a re-check of a prior evaluation that scored requirement_coverage=0.9167 and claimed R3
(the `?author=` filter) is not met because `wrap-params` middleware is missing.

**The first evaluator was CORRECT.** Verified against the code:

- `src/book_api/core.clj:59-61` — `handler` threads only `wrap-json-body` and `wrap-json-response`. No `ring.middleware.params/wrap-params`.
- `src/book_api/core.clj:37` — reads `(get-in request [:query-params "author"])`. In Ring, `:query-params` is populated **only** by `wrap-params`; the Jetty adapter populates `:query-string`, and `ring-json` touches body/response only. So over real HTTP the author arg is always `nil` and `db/list-books` returns every book.
- `src/book_api/db.clj:49-52` — the db-layer filter is implemented correctly, but it is never reached with a non-nil author over HTTP.
- `test/book_api/core_test.clj:34` — the filter test hand-injects `:query-params {"author" "Herbert"}` and calls `core/app` directly (not `core/handler`), bypassing the middleware stack, so the passing test gives false confidence.

`ring-core` (which provides `wrap-params`) is present in `deps.edn:3` but never required or applied, confirming the omission is a wiring bug, not a dependency gap.

Re-scored requirement_coverage = 11/12 = **0.9167** (unchanged). R3 reclassified from "missing" to **partial** — the filter logic exists end-to-end but is non-functional over HTTP.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `core.clj:39-42` → `db/create-book!` (`db.clj:57-70`) |
| R2 | GET /books lists all | ✓ implemented | `core.clj:36-37` → `db/list-books` (`db.clj:49-52`) |
| R3 | GET /books ?author= filter | ~ partial | `core.clj:37` reads `:query-params` but `wrap-params` absent (`core.clj:59-61`); nil over HTTP → lists all |
| R4 | GET /books/{id} single | ✓ implemented | `core.clj:47` → `db/get-book` (`db.clj:54-55`), 404 on miss |
| R5 | PUT /books/{id} update | ✓ implemented | `core.clj:49-52` → `db/update-book!` (`db.clj:72-81`) |
| R6 | DELETE /books/{id} | ✓ implemented | `core.clj:53` → `db/delete-book!` (`db.clj:83-87`), 204/404 |
| R7 | SQLite storage | ✓ implemented | `db.clj:7-9` `jdbc:sqlite:`, `org.xerial/sqlite-jdbc` dep |
| R8 | JSON responses + status codes | ✓ implemented | `wrap-json-response` (`core.clj:61`), 201/200/404/400/204/405 |
| R9 | Validation: title & author required | ✓ implemented | `valid-book?` (`core.clj:8-13`), 400 at `core.clj:42` |
| R10 | GET /health | ✓ implemented | `core.clj:33-34` returns `{:status "ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, run, API sections |
| R12 | ≥ 3 tests | ✓ implemented | 3 `deftest` in `core_test.clj`; test_coverage=1.0 |

## Build & Test

Not re-run (per skill §2). Read from `scores.json`:

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 0.95
defect_rate   = 0.7727
```

3 `deftest` forms (`health-check`, `create-validate-and-read-book`, `list-filter-update-and-delete`), 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 153 (core.clj 66 + db.clj 87) |
| Lines of code (tests) | 51 |
| Files (source + test) | 4 |
| Dependencies | 5 (deps.edn) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

1. [high] R3 — `?author=` filter never works over HTTP; `wrap-params` middleware missing (`core.clj:59-61` / `:37`).

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel)/experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json
grep -n "query-params\|wrap-params\|wrap-json" src/book_api/core.clj
grep -n "query-params" test/book_api/core_test.clj
```
