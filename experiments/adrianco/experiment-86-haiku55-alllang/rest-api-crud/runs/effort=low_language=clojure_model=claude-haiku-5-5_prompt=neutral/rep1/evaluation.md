# Evaluation: rest-api-crud · effort=low language=clojure model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — from test_coverage=1.0
- **Build:** pass — not re-run (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored scores (`scores.json`): test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.931, idiomatic=0.82, token_efficiency=0.0218. The run is not yet in `retort.db` (inline gate), so `scores.json` is the authoritative source.

## Requirements

Checklist from the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handler.clj:76-78` → `db.clj:22 create-book!`; test `create-and-get-book` api_test.clj:42 |
| R2 | GET /books lists all | ✓ implemented | `handler.clj:72-75` → `db.clj:38 list-books`; test api_test.clj:72 |
| R3 | GET /books ?author= filter | ✓ implemented | `handler.clj:72-74`, `db.clj:40-41` (COLLATE NOCASE); test api_test.clj:74 |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `handler.clj:83-85` → `db.clj:31 get-book`; 404 at :85 |
| R5 | PUT /books/{id} updates | ✓ implemented | `handler.clj:86-90` → `db.clj:43 update-book!`; test `update-book` api_test.clj:80 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handler.clj:91-93` → `db.clj:51 delete-book!`; test `delete-book` api_test.clj:95 |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `deps.edn` org.xerial/sqlite-jdbc; `db.clj:15-20` get-datasource :dbtype sqlite |
| R8 | JSON responses + status codes | ✓ implemented | `handler.clj:7-13 respond` sets JSON content-type; 201/200/204/404/405/422/400/500 used |
| R9 | Validation: title & author required | ✓ implemented | `handler.clj:33-40 validation-errors`, enforced at :51-53; test `create-validates-required-fields` api_test.clj:54 (see info finding on 422) |
| R10 | GET /health | ✓ implemented | `handler.clj:65-68` returns 200 {status ok}; test `health-check` api_test.clj:37 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Requirements, Run, Test, API, Errors, Examples sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 `deftest` in `test/books/api_test.clj`; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores are authoritative per the evaluate-run skill.

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.9306, "idiomatic": 0.82, "token_efficiency": 0.0218}
# test_coverage=1.0 ⇒ `clojure -M:test` built the project and all tests passed.
```

Test command (per README / deps.edn `:test` alias): `clojure -M:test` → `books.runner/-main` runs `books.api-test`. 7 deftests, no `t/skip`/disabled tests found (`grep` over test/).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 173 (core 11 + db 54 + handler 108) |
| Lines of code (tests) | 118 (api_test 110 + runner 8) |
| Files (source + test) | 5 |
| Dependencies (deps.edn) | 6 runtime + 1 test (ring-mock) |
| Tests total | 7 deftests |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | not measured (not re-run) |

## Findings

Full list in `findings.jsonl` (both info-level — no deductions):

1. [info] R9 — validation failures return 422 where the requirement hint says 400 (422 is the correct code for a well-formed body failing validation; a non-object body does return 400; both documented in README).
2. [info] R3 — `?author=` filter is case-insensitive exact match (documented, spec-compliant).

No critical/high/medium/low findings. This is a clean, idiomatic, fully-tested implementation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                              # stored mechanical scores (authoritative)
cat ../../REQUIREMENTS.json                  # pinned 12-item checklist
grep -rc deftest test/books/api_test.clj     # 7 tests
grep -rnE "t/skip|\^:skip" test/             # (none) no skipped tests
# clojure -M:test                            # would rebuild + run tests (scores say pass)
```
