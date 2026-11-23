# Evaluation: agent=codex effort=low language=clojure model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + all tests executed and passed)
- **Lint:** pass — `code_quality=0.906` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Stored scores (`scores.json`): test_coverage=1.0, code_quality=0.906, defect_rate=0.68,
maintainability=0.649, idiomatic=0.78, token_efficiency=0.013. The run is not yet in
`retort.db` (inline-gate case), so `scores.json` is the authoritative score source per the skill.

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.clj:45-48` INSERT ... RETURNING *, 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `books.clj:42-44` SELECT * ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `books.clj:41-43` WHERE author=? branch; test `books_test.clj:44-46` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `books.clj:56-60`; `missing` 404 when no row |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `books.clj:57-60` UPDATE ... RETURNING * |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `books.clj:52-54` DELETE, 404 when 0 rows |
| R7 | Data stored in SQLite | ✓ implemented | `deps.edn:5` org.xerial/sqlite-jdbc; `books.clj:8-13` CREATE TABLE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `books.clj:15-17` JSON body/content-type; 201/200/400/404/405/500 used |
| R9 | Validation: title and author required | ✓ implemented | `books.clj:31-32` nonblank-string check → 400; test `books_test.clj:48-55` |
| R10 | GET /health health-check | ✓ implemented | `books.clj:67` returns {:status "ok"}; test `books_test.clj:58` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md:1-27` setup, run, endpoint table, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 `deftest`s in `books_test.clj`; test_coverage=1.0 |

No partial/missing requirements and no enhancements that change the spec verdict.

## Build & Test

Not re-run — stored scores used per skill (test_coverage=1.0 ⇒ build + all tests passed).

```text
scores.json: {"test_coverage": 1.0, "code_quality": 0.906, "defect_rate": 0.68,
              "maintainability": 0.649, "idiomatic": 0.78, "token_efficiency": 0.013}
```

Test command (for reference, from `deps.edn`): `clojure -M:test` → `books-test/-main` runs 4 deftests.
Skip scan: `grep -cE "(deftest" books_test.clj` = 4; no `.skip`, `#_`, or disabled tests found → 4 effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 144 (books.clj 80, books_test.clj 64) |
| Files | 11 (incl. logs/meta; 3 source: books.clj, books_test.clj, deps.edn) |
| Dependencies | 5 (`deps.edn`: clojure, data.json, java.jdbc, sqlite-jdbc, ring-jetty-adapter) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no action required:

1. [info] enh-1 — Create/update use INSERT/UPDATE ... RETURNING * for a single round-trip echo
2. [info] enh-2 — Centralized validation via ex-info keeps route code clean
3. [info] info-1 — DELETE returns 200 with {id} body rather than 204 (acceptable per spec)

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6.2-astra_prompt=neutral/rep1
cat scores.json                      # stored mechanical scores (test_coverage=1.0)
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
grep -cE "\(deftest" books_test.clj   # 4 tests, 0 skips
wc -l books.clj books_test.clj        # 144 LOC
# optional (not required): clojure -M:test
```
