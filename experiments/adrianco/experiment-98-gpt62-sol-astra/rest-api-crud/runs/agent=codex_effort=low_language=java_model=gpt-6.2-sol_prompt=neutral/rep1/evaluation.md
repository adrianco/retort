# Evaluation: agent=codex effort=low language=java model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=1.0 from scores.json)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** Spring Boot MVC — `BookController` (REST) → `BookRepository` (JdbcClient) → SQLite via `schema.sql`; `Book` record with `Book.Input` validation record. run-summary skill not invoked (unavailable).
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookController.java:33-37`, `BookRepository.java:25-31` (INSERT … RETURNING) |
| R2 | GET /books lists all | ✓ implemented | `BookController.java:39-42`, `BookRepository.java:33-35` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookController.java:40` `@RequestParam author`, `BookRepository.java:36-38` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BookController.java:44-47` `orElseThrow(notFound)`, repo `find` 41-44 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookController.java:49-52`, `BookRepository.java:46-51` (UPDATE … RETURNING) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookController.java:54-60` (204 / 404), repo `delete` 54-55 |
| R7 | SQLite / embedded DB | ✓ implemented | `pom.xml:28-32` sqlite-jdbc, `application.properties:1` `jdbc:sqlite:books.db`, `schema.sql` |
| R8 | JSON + correct status codes | ✓ implemented | 201 `created` (:36), 200, 404 `ResponseStatusException` (:62-63), 400 validation, 204 `noContent` (:59); problemdetails enabled |
| R9 | Validation: title & author required | ✓ implemented | `Book.java:6` `@NotBlank` on title/author, `@Valid` at `:34,:50`; tested `BookApiTest.java:110-131` |
| R10 | GET /health | ✓ implemented | `BookController.java:28-31` returns `{"status":"UP"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, env vars, endpoint table, curl example |
| R12 | ≥ 3 tests | ✓ implemented | `BookApiTest.java` 4 `@Test` methods; test_coverage=1.0 |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   → build succeeded and all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
maintainability = 0.728
idiomatic     = 0.86
```

Test suite (`BookApiTest.java`, MockMvc over a real SpringApplication with a temp SQLite file):
- `healthAndEmptyCollection` — /health UP, empty list
- `createsReadsUpdatesAndDeletesBook` — full CRUD + 404 paths
- `filtersBooksByExactAuthorAfterRestart` — persistence across restart + exact author filter
- `rejectsMissingAndBlankFieldsAndMalformedJson` — 400 validation on missing/blank title/author and malformed JSON

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. test) | 294 |
| Main Java LOC | 145 |
| Test LOC | 139 |
| Files (src) | 7 |
| Dependencies (pom) | 5 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

No correctness, build, or test defects. Only one informational note:

1. [info] PUT /books/{id} is full-replace (year/isbn reset to null when omitted) — valid PUT semantics, documented in README; no change required.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                                  # mechanical scores (build/test/lint)
mvn clean verify                                 # full build + 4 tests (optional re-run)
```
