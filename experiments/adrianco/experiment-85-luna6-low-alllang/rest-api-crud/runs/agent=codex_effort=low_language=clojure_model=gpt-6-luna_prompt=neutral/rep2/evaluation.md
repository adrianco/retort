# Evaluation: agent=codex effort=low language=clojure model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=clojure, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (repair task — previous attempt's `?author=` HTTP bug is fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 deftests (all pass) / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.967` (scores.json)
- **Architecture:** `run-summary` skill unavailable in this session; see source notes below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

This is a REPAIR run. `FEEDBACK.md` flagged that the prior attempt (a) did not fully
pass build/tests and (b) the `?author=` filter never worked over real HTTP because
`wrap-params` middleware was missing. Both are now resolved: `core.clj` threads
`wrap-params` into the handler, and `core_test.clj` adds an assertion using the raw
`:query-string` shape an HTTP server produces.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `core.clj:28` POST handler → `db.clj:21 create-book!` selects `:title :author :year :isbn` |
| R2 | GET /books lists all | ✓ implemented | `core.clj:24` → `db.clj:13 list-books` |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:50 wrap-params`; `db.clj:14` filters `LOWER(author)=LOWER(?)`; test `core_test.clj:28` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `core.clj:38-40` returns 200/404 via `db/find-book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `core.clj:41-45` → `db.clj:31 update-book!` |
| R6 | DELETE /books/{id} | ✓ implemented | `core.clj:46-48` → `db.clj:40 delete-book!` |
| R7 | SQLite / embedded DB | ✓ implemented | `deps.edn` org.xerial/sqlite-jdbc; `db.clj:6 jdbc:sqlite:` |
| R8 | JSON responses + status codes | ✓ implemented | `wrap-json-response` (`core.clj:51`); 201/200/204/400/404 returned |
| R9 | title & author required (400) | ✓ implemented | `core.clj:11 valid-book?`; test `core_test.clj:33` asserts 400 |
| R10 | GET /health | ✓ implemented | `core.clj:21` returns `{:status "ok"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `clojure -M:run` / `-M:test`, PORT/BOOKS_DB |
| R12 | ≥ 3 tests that run | ✓ implemented | 3 `deftest` in `core_test.clj`; `test_coverage=1.0` |

## Build & Test

Build/test were not re-run — stored scores are authoritative (this run is an inline
gate run, so it is not yet in `retort.db`; `scores.json` holds the computed scores):

```text
scores.json
test_coverage   = 1.0    (build + all tests passed)
code_quality    = 0.967
defect_rate     = 0.841
maintainability = 0.985
idiomatic       = 0.800
```

No skipped/disabled tests found (`grep` for `comment`/`#_`/`:disabled` → none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 146 (src 95, test 51) |
| Files | 15 (incl. logs/archive meta) |
| Dependencies | 6 (deps.edn) |
| Tests total | 3 deftests |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R3 prior `?author=` HTTP failure is fixed — `wrap-params` present + regression test

No critical/high/medium/low findings. The run meets every pinned requirement.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json              # stored build/test/lint scores (authoritative)
grep -n wrap-params src/book_api/core.clj
clojure -M:test              # optional: re-run tests (builds too)
```
