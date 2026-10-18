# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 2

> SECOND OPINION — re-check of a prior evaluation (requirement_coverage=0.9167, R3 flagged NOT met).

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (builds + all tests pass) — but one spec'd feature (R3) is non-functional over real HTTP
- **Requirements:** 11/12 implemented, 1 partial (R3), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests ran)
- **Lint:** pass — code_quality=0.9667 from scores.json
- **Findings:** 1 item in `findings.jsonl` (0 critical, 1 high)

## Second-opinion verdict on the prior claim

**Prior claim (R3): "?author= filter never works over real HTTP — wrap-params middleware missing." → CONFIRMED. The first evaluator was correct.**

I went looking for the implementation before accepting it as missing:

- `src/book_api/core.clj:16` destructures `:query-params` from the request; `core.clj:22` reads `(get query-params "author")` and passes it to `db/list-books`.
- The middleware chain at `core.clj:46-47` is **only** `(wrap-json-body {:keywords? true})` then `wrap-json-response`.
- In Ring, `:query-params` is populated **exclusively** by `ring.middleware.params/wrap-params` (which includes `wrap-query-params`). A grep over `src/` and `test/` finds **no** `wrap-params`, `wrap-query-params`, or `middleware.params` anywhere. The require block (`core.clj:1-5`) does not pull it in.
- Therefore, over real HTTP via jetty (`core.clj:49-52`), a `GET /books?author=Foo` request arrives with `:query-string "author=Foo"` but **no** `:query-params` key → `query-params` is `nil` → `(get nil "author")` is `nil` → `db/list-books` receives `author=nil` → returns **all** books.
- The db-level filter itself is present and correct (`db/db.clj:12-15`, case-insensitive `WHERE LOWER(author)=LOWER(?)`), so the capability exists but is **unreachable on the wire**.
- `test/book_api/core_test.clj:24` injects `:query-params {"author" "frank herbert"}` directly into the handler map, bypassing the HTTP/middleware layer — so the passing test masks the defect exactly as the first evaluator described.

Classification: **partial** (code genuinely attempts R3 and the db filter works, but the HTTP wiring is broken), which for coverage counts as not-fully-met — same denominator effect as the first evaluator's score.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `core.clj:24-27`, `db.clj:20-29`; test `core_test.clj:21-22` |
| R2 | GET /books lists all | ✓ implemented | `core.clj:21-22`, `db.clj:12-15`; test `core_test.clj:23` |
| R3 | GET /books ?author= filter | ~ partial | db filter `db.clj:12-15` correct, but `wrap-params` missing (`core.clj:46-47`) → `query-params=nil` over HTTP; test `core_test.clj:24` injects params directly |
| R4 | GET /books/{id} | ✓ implemented | `core.clj:30-35`, `db.clj:17-18`; test `core_test.clj:36,39` |
| R5 | PUT /books/{id} | ✓ implemented | `core.clj:36-40`, `db.clj:31-38`; test `core_test.clj:37` |
| R6 | DELETE /books/{id} | ✓ implemented | `core.clj:41-43`, `db.clj:40-41`; test `core_test.clj:38` |
| R7 | SQLite / embedded DB | ✓ implemented | `db.clj:5-6` `jdbc:sqlite:`, `deps.edn:7` sqlite-jdbc |
| R8 | JSON + status codes | ✓ implemented | `wrap-json-response` `core.clj:47`, `response` helper `core.clj:7-8`, codes 200/201/400/404/204/405 |
| R9 | Validation (title+author) | ✓ implemented | `valid-book?` `core.clj:10-13`, 400 at `core.clj:26,36`; test `core_test.clj:28` |
| R10 | GET /health | ✓ implemented | `core.clj:18-19`; test `core_test.clj:29` |
| R11 | README with setup/run | ✓ implemented | `README.md` present with Requirements/Run/endpoints sections |
| R12 | ≥3 tests | ✓ implemented | 3 deftests in `core_test.clj`; test_coverage=1.0, no skips |

## Build & Test

```text
scores.json (scorers already ran — not re-run per skill step 2)
test_coverage=1.0  ⇒ build + all tests passed
code_quality=0.9667  defect_rate=0.8333  maintainability=0.9870  idiomatic=0.8
```

No skipped/disabled tests (`grep` for skip/ignore in test/ → none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 93 (core.clj 52 + db.clj 41) |
| Lines of test | 47 (core_test.clj 39 + test_runner.clj 8) |
| Files | 16 |
| Dependencies | 6 (deps.edn) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [high] R3 — ?author= filter never works over real HTTP; `wrap-params` middleware missing (`core.clj:46-47`), test masks it by injecting `:query-params` (`core_test.clj:24`).

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json
grep -rn "wrap-params\|wrap-query-params\|middleware.params\|query-params" src test
```
