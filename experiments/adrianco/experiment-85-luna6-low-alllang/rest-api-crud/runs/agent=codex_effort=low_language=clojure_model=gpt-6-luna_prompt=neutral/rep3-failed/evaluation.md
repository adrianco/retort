# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 3

> **SECOND OPINION.** This run was re-checked against a first evaluation that scored
> `requirement_coverage=0.9167` and claimed R3 (the `?author=` filter) was not met.
> **The first evaluator was correct.** I went looking for the implementation and it is
> genuinely non-functional on a live server — see R3 below. The score stands: 0.9167.

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (build + tests pass; one requirement partial)
- **Requirements:** 11/12 implemented, 1 partial (R3), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (implied by `test_coverage=1.0`, not re-run)
- **Lint:** n/a — `code_quality=0.9167` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 1 medium)

## Second-opinion verdict on R3

**Claim re-checked:** "?author= filter is non-functional on a live server — no wrap-params middleware."

**Verdict: CONFIRMED — the first evaluator was right.** I searched for the implementation before accepting it was broken:

- `src/book_api/core.clj:26` — `(GET "/books" req (response 200 (db/all-books (get-in req [:params :author]))))` reads the author from `:params`.
- `src/book_api/core.clj:44` — the handler stack is `(-> app-routes wrap-json-response (wrap-json-body {:keywords? true}))`. There is **no** `ring.middleware.params/wrap-params`.
- `grep` for `wrap-params`, `query-params`, `handler/site`, `wrap-defaults` across `src/ test/ deps.edn` returns **nothing**.
- Compojure merges only **route**-params into `:params`; `/books` has no route params, so a query-string `author=...` stays in `:query-string` and `(get-in req [:params :author])` is always `nil`.
- `src/book_api/db.clj:34-43` genuinely supports the filter (`WHERE author = ?`), but it is only ever called with `nil`, so `GET /books?author=X` returns **all** books.

So the DB layer exists but the wiring to reach it does not. R3 is **partial**, not implemented. Coverage = 11/12 = **0.9167** (unchanged).

Secondary finding uncovered while verifying: the one test meant to exercise R3 (`test/book_api/core_test.clj:26`) passes vacuously — it asserts `count == 1`, and the not-found error map `{:error "Not found"}` also has count 1. That is why a broken filter still scored `test_coverage=1.0`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/book_api/core.clj:21-25`, `db/create-book` `db.clj:57-62` |
| R2 | GET /books lists all | ✓ implemented | `src/book_api/core.clj:26`, `db/all-books` `db.clj:34-43` |
| R3 | GET /books ?author= filter | ~ partial | `core.clj:26` reads `:params :author` but `core.clj:44` has no `wrap-params`; always nil → returns all books |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `src/book_api/core.clj:27-30` |
| R5 | PUT /books/{id} update | ✓ implemented | `src/book_api/core.clj:31-37`, `db/update-book` `db.clj:64-68` |
| R6 | DELETE /books/{id} + 204/404 | ✓ implemented | `src/book_api/core.clj:38-41`, `db/delete-book` `db.clj:70-73` |
| R7 | SQLite / embedded DB | ✓ implemented | `db.clj:1-18` JDBC sqlite, `deps.edn` `org.xerial/sqlite-jdbc` |
| R8 | JSON responses + status codes | ✓ implemented | `response` fn `core.clj:9-10`, `wrap-json-response` `core.clj:44` |
| R9 | validation: title+author required | ✓ implemented | `valid-book?` `core.clj:12-17`, 400 at `core.clj:25` |
| R10 | GET /health | ✓ implemented | `src/book_api/core.clj:20` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-33` |
| R12 | ≥3 tests that run | ✓ implemented | 3 `deftest` in `core_test.clj`, `test_coverage=1.0` |

## Build & Test

Not re-run — read from `scores.json` (inline gate during `retort run`):

```text
test_coverage = 1.0   (build + all 3 tests passed)
code_quality  = 0.9167
defect_rate   = 0.3846
```

Tests (`clojure -M:test`): 3 `deftest`, 0 skips (grep for skip markers returned none). Note the `author-filter-and-crud` test does not actually verify R3 (see findings).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 121 (core 48 + db 73) |
| Test LOC | 30 |
| Source files | 3 clj + deps.edn + README |
| Dependencies | 6 (deps.edn) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] R3 — `?author=` filter non-functional on a live server (no `wrap-params`); DB filter unreachable with a value.
2. [medium] `author-filter-and-crud` test passes vacuously (`count` of the 404 error map is also 1), so it never verifies R3.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json
grep -rn ":params\|wrap-params\|query-params" src/        # only core.clj:26, no middleware
grep -rn "deftest\|skip" test/                            # 3 deftests, 0 skips
```
