# Evaluation: effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=clojure, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 deftests / 18 `is` assertions passed / 0 skipped (all effective)
- **Build:** pass (test_coverage=1.0 from scores.json — build + all tests passed)
- **Lint:** pass (code_quality=0.956 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored scores (`scores.json`): test_coverage=1.0, defect_rate=1.0, maintainability=1.0, code_quality=0.956, idiomatic=0.7, token_efficiency=0.0095.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `core.clj:63-68` POST /books → INSERT ... RETURNING *, 201 |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:55-62` SELECT * ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:55-61` WHERE author = ?; test `list-with-author-filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `core.clj:69-71` find-book → 200/404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `core.clj:72-79` UPDATE ... WHERE id=?, 200; 404 if missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `core.clj:80-84` DELETE ... update-count → 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `core.clj:13-19` next.jdbc datasource dbtype sqlite; deps.edn sqlite-jdbc |
| R8 | JSON responses with correct status codes | ✓ implemented | `core.clj:21-24` resp sets Content-Type json; 201/200/404/400/204 used |
| R9 | Input validation: title and author required | ✓ implemented | `core.clj:28-34` validate; test `validation` asserts 400 + error list |
| R10 | GET /health health check | ✓ implemented | `core.clj:54` GET /health → {status "ok"}; test `health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` documents deps, `clojure -M:run`, `-M:test`, endpoints |
| R12 | At least 3 tests | ✓ implemented | `test/books/core_test.clj` 4 deftests, 18 assertions; test_coverage=1.0 |

No prompt-factor requirements (prompt=neutral maps to no `prompts/<level>.md` checklist).

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=1.0  → build + all tests passed (test gate)
             defect_rate=1.0    → build+test succeeded
             code_quality=0.956 → lint/quality (Lint: pass)
```

```text
clojure -M:test   (cognitect test-runner)
4 deftests: health, crud-lifecycle, validation, list-with-author-filter
18 `is` assertions; 0 skipped/disabled markers found (grep)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 91 (src) + 53 (test) = 144 |
| Files | 12 (incl. logs/meta); 2 source |
| Dependencies | 8 (deps.edn mvn/git) |
| Tests total | 4 deftests / 18 assertions |
| Tests effective | 4 / 18 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (scores read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Author filter uses a manual raw-query-string fallback (`core.clj:56-59`) redundant with Ring's parsed params.
2. [info] Create/update depend on SQLite `RETURNING *` (requires sqlite-jdbc ≥ 3.35, pinned 3.44).

No critical/high/medium/low findings — a clean, complete implementation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=clojure_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rcE "\(deftest" test/           # test count
grep -rnE "\^:skip|#_\(deftest|\(comment" test/ src/   # skip markers (none)
# full build/test (optional, not required for eval):
clojure -M:test
```
