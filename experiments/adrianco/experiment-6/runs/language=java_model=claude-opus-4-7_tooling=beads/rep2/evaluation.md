# Evaluation: language=java_model=claude-opus-4-7_tooling=beads · rep 2

## Summary

- **Factors:** language=java, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db (build+tests passed)
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill not invoked (inline evaluation)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `BookController.java:22` — `@PostMapping` accepting `@Valid @RequestBody Book`; fields in `Book.java:16-24` |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:29` — `@GetMapping` returning `repository.findAll()` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookController.java:30-31` — `@RequestParam author` with `repository.findByAuthor(author)`; `BookRepository.java:8` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `BookController.java:37-40` — `@GetMapping("/{id}")` with 404 on missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookController.java:44-53` — `@PutMapping("/{id}")` updates all fields, 404 on missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookController.java:57-62` — `@DeleteMapping("/{id}")` with 204 response, 404 on missing |
| R7 | Data stored in SQLite | ✓ implemented | `application.properties:1` — `jdbc:sqlite:books.db`; `pom.xml:43` — sqlite-jdbc dependency; `pom.xml:47` — hibernate-community-dialects |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 Created (`BookController.java:25`), 200 OK (`BookController.java:39,51`), 204 No Content (`BookController.java:62`), 404 Not Found (`BookController.java:40,53,59`), 400 Bad Request (`ValidationExceptionHandler.java:23`) |
| R9 | Input validation: title and author required | ✓ implemented | `Book.java:16-19` — `@NotBlank` on title and author; `ValidationExceptionHandler.java:15-25` returns 400 with field errors |
| R10 | GET /health health-check endpoint | ✓ implemented | `HealthController.java:10-14` — returns `{"status":"ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — build/run commands, endpoint table, curl examples, status code docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookControllerTests.java` — 7 `@Test` methods: health, create+persist, validation 400, filter by author, update, delete, 404 |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage = 1.0 (build + all tests passed)
  code_quality  = 1.0
  defect_rate   = 1.0
```

```text
Test suite: BookControllerTests.java
  7 @Test methods, 0 @Disabled/@Ignore
  - healthEndpointReturnsOk
  - createBookReturns201AndPersists
  - createBookWithoutTitleReturns400
  - listBooksFiltersByAuthor
  - updateBookChangesFields
  - deleteBookRemovesIt
  - getMissingBookReturns404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 289 (Java) |
| Files | 19 |
| Dependencies | 6 (Maven) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | N/A (scores from DB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Test uses in-memory SQLite rather than file-backed DB for integration tests

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-7_tooling=beads/rep2
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE "@Disabled|@Ignore" src/test --include="*.java" | wc -l
grep -c "@Test" src/test/java/com/example/booksapi/BookControllerTests.java
find . -name "*.java" -not -path "*/target/*" | xargs wc -l
```
