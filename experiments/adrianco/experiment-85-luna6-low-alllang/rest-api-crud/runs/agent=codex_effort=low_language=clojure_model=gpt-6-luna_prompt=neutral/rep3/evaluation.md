# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral (repair task)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `test_coverage=1.0`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests ran and passed)
- **Lint:** pass — code_quality=0.95 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

This is a repair run. FEEDBACK.md flagged two problems in the prior attempt: build/tests
not fully passing, and a non-functional `?author=` filter (missing `wrap-params`). Both are
fixed here — `wrap-params` is now in the middleware stack (`core.clj:60`) and the list route
reads `:query-params`, and `test_coverage=1.0` confirms the whole suite now runs and passes.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `core.clj:25` POST route → `db/create-book` (`db.clj:58`), persists all four fields |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:31` → `db/all-books` (`db.clj:34`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `core.clj:31` reads `:query-params :author`; `db.clj:38` WHERE author=?; test `query-params-work-through-ring-middleware` |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `core.clj:34` → `db/find-book`, 404 branch present |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `core.clj:38` → `db/update-book` (`db.clj:65`), 404 when absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `core.clj:45` → `db/delete-book` (`db.clj:70`), 204/404 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `db.clj:8` `jdbc:sqlite:` via sqlite-jdbc dep (`deps.edn`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `wrap-json-response` (`core.clj:58`); 201/200/204/400/404 across routes |
| R9 | Input validation: title & author required | ✓ implemented | `valid-book?` (`core.clj:13`) rejects blank title/author → 400; test `create-requires-title-and-author` |
| R10 | GET /health | ✓ implemented | `core.clj:23` returns `{:status "ok"}` 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` covers run, env vars, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `deftest` in `core_test.clj`; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per skill (compiled/JVM re-runs are the slowest step).

```text
scores.json: test_coverage=1.0  code_quality=0.95  defect_rate=0.7403
             maintainability=0.8821  idiomatic=0.55  token_efficiency=0.0028
```

`test_coverage=1.0` ⇒ `clojure -M:test` built the project and all 5 deftests passed. The
`:test` alias exits non-zero on any fail/error (`deps.edn`), so a green score means a clean run.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 178 (src 132, test 46) |
| Files | 14 |
| Dependencies | 7 (deps.edn) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

No critical/high/medium findings. Three low/info observations (full list in `findings.jsonl`):

1. [low] Raw `java.sql` JDBC instead of an idiomatic wrapper (next.jdbc) — idiomatic=0.55
2. [info] Single shared JDBC connection via atom rather than a pool
3. [info] README omits the `books.db` default-path detail

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                 # stored mechanical scores (test_coverage=1.0 = build+tests pass)
cat REQUIREMENTS.json           # pinned 12-requirement checklist
grep -c deftest test/book_api/core_test.clj
# Optional full re-run (slow): clojure -M:test
```
