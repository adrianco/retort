# Evaluation: effort=low_language=clojure_model=claude-fable-5-2_prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (implied by `test_coverage=1.0`; Clojure tests build the code)
- **Lint:** pass — `code_quality=1.0` from `scores.json`, 0 warnings
- **Architecture:** `src/books/core.clj` (Ring/Compojure handler + validation) over `src/books/db.clj` (next.jdbc + SQLite); `-main` wires a datasource into the handler on Jetty. Clean two-namespace separation of HTTP and persistence.
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `core.clj:71` POST route → `db/create-book!` `db.clj:35` (INSERT … RETURNING) |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:67` → `db/list-books` `db.clj:26` |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:68-70` reads `author` param; `db.clj:30-31` filtered SQL; `list-and-filter-test` `core_test.clj:74` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `core.clj:73-76`; `db/get-book` `db.clj:23`; `not-found-test` `core_test.clj:99` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `core.clj:77-83`; `db/update-book!` `db.clj:42`; `update-test` `core_test.clj:84` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `core.clj:84-87`; `db/delete-book!` `db.clj:51`; `delete-test` `core_test.clj:93` |
| R7 | Data stored in SQLite | ✓ implemented | `db.clj:7-10` sqlite datasource; schema `db.clj:15-20`; deps `org.xerial/sqlite-jdbc` |
| R8 | JSON responses + correct status codes | ✓ implemented | `json-response` `core.clj:11`; 201/200/204/404/400 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `validate` `core.clj:32-44`; `validation-test` `core_test.clj:49` |
| R10 | GET /health | ✓ implemented | `core.clj:66`; `health-test` `core_test.clj:28` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Requirements/Run/Test/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 `deftest` in `core_test.clj`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (inline gate output) — build/test not re-run per skill guidance.

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 1.0   → lint clean
defect_rate   = 1.0   → build+test succeeded
```

Test count (grep): 9 `deftest` forms; 0 skip/ignore markers.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 150 (core 95 + db 55) |
| Test lines | 102 |
| Files | 11 (3 source/test .clj + deps.edn + README + metadata) |
| Dependencies | 8 runtime + 2 test (deps.edn) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| token_efficiency | 0.0211 (from scores.json) |
| idiomatic | 0.87 (from scores.json) |
| maintainability | 0.954 (from scores.json) |

Notable strengths (beyond spec, not deductions): per-route param parsing avoids `wrap-params` consuming form-encoded bodies (`core.clj:64-70`), with a dedicated `form-content-type-body-test`; `read-body` distinguishes malformed/non-object JSON → 400; `parse-id` guards against overflow with a bounded digit regex.

## Findings

None. Clean run — all requirements implemented, all tests pass, no skipped/disabled tests, lint clean.

## Reproduce

```bash
cd experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=clojure_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                 # stored build/test/lint scores
grep -c "deftest" test/books/core_test.clj
clojure -M:test                 # (optional) re-run: build + 9 tests
```
