# Evaluation: agent=codex effort=low language=java model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=Spring Boot 3.4.5
- **Status:** ok (repair task — previous attempt had failed; this attempt builds and all tests pass)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** run-summary skill unavailable in this session; see inline notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookController.java:18-20` create; `BookRepository.java:28-46` INSERT all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:23` list; `BookRepository.java:48-50` SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.java:51` `WHERE author = ?`; test `filtersUpdatesAndDeletesBooks` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `BookController.java:26` → `BookNotFoundException`; `ApiExceptionHandler.java:14-18` 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookController.java:29-31`; `BookRepository.java:58-62` UPDATE |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookController.java:34-37` 204; `BookRepository.java:64-66` DELETE |
| R7 | Data stored in SQLite | ✓ implemented | `pom.xml` org.xerial:sqlite-jdbc; `application.properties:1` jdbc:sqlite; `BookRepository.java:25` CREATE TABLE |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 create, 200 list/get/put, 204 delete, 404/400 via `ApiExceptionHandler` |
| R9 | Validation: title & author required | ✓ implemented | `BookRequest.java:6-7` `@NotBlank`; test `validatesRequiredTitleAndAuthor` → 400 |
| R10 | GET /health | ✓ implemented | `HealthController.java:11` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Requirements, Run, Endpoints, Tests sections |
| R12 | ≥ 3 tests that run | ✓ implemented | `BookApiIntegrationTest.java` 4 `@Test` methods; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 1.0   (build + all tests passed)
code_quality    = 1.0
defect_rate     = 1.0   (build+test succeeded)
maintainability = 0.9116
idiomatic       = 0.3
```

Test suite: `BookApiIntegrationTest` — `@SpringBootTest` + `@AutoConfigureMockMvc`, DB cleared `@BeforeEach`. Covers create+read, validation (400), filter/update/delete lifecycle, and health.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 168 |
| Lines of code (test) | 65 |
| Files (excl. target/.git) | 22 |
| Dependencies (pom.xml) | 11 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] Low idiomatic score (0.3) despite clean build/tests — terse single-line class bodies
2. [info] `create()` fallback selects last row by id if the key holder misses (dead path, not concurrency-safe)

No requirement, build, test, or skip findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build/test not re-run)
grep -rEn "@Disabled|@Ignore|assumeTrue" src --include="*.java"   # 0 skips
grep -rc "@Test" src/test/java/com/example/books/BookApiIntegrationTest.java
# mvn test   # only if re-verifying from scratch
```
