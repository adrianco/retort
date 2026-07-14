# Evaluation: language=java_model=claude-opus-4-7_tooling=none · rep 2

## Summary

- **Factors:** language=java, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=1.0 from retort.db (build+tests succeeded)
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----| 
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `BookController.java:29` — `@PostMapping create(@Valid @RequestBody Book)` accepts all four fields |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:36` — `list()` returns `repository.findAll()` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookController.java:37` — `@RequestParam(required = false) String author` with `findByAuthor` |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `BookController.java:44` — `@GetMapping("/{id}")`, returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookController.java:51` — `@PutMapping("/{id}")`, updates all fields, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookController.java:61` — `@DeleteMapping("/{id}")`, returns 204, 404 if absent |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | `application.properties:1` — `jdbc:h2:file:./data/books` (H2 file-mode, Java's SQLite equivalent) |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | `BookController.java` — 201 Created, 200 OK, 204 No Content, 404 Not Found, 400 Bad Request |
| R9 | Input validation: title and author are required | ✓ implemented | `Book.java:18,21` — `@NotBlank` on title and author; `ValidationExceptionHandler.java` returns 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `HealthController.java:11` — `@GetMapping("/health")` returns `{"status":"UP"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents build, run, test commands and full API reference |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookControllerTest.java` — 8 integration tests using `@SpringBootTest` + `@AutoConfigureMockMvc` |

## Build & Test

```text
Build and test scores from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 1.0
  defect_rate   = 1.0
```

```text
Tests (from source inspection):
  8 @Test methods in BookControllerTest.java
  0 @Disabled / @Ignore annotations
  All tests exercise real Spring context (SpringBootTest + MockMvc)
  
  Test coverage:
  - healthEndpointReturnsUp — R10
  - createBookReturns201AndPersistsIt — R1, R4, R8
  - createWithoutTitleReturns400 — R9
  - createWithoutAuthorReturns400 — R9
  - listFilteredByAuthorOnlyReturnsMatchingBooks — R2, R3
  - updateBookChangesFields — R5
  - deleteBookReturns204AndRemovesIt — R6
  - getNonExistentBookReturns404 — R4, R8
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 335 (Java) |
| Files | 15 |
| Dependencies | 5 (Maven) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Scores from retort.db

| Metric | Score |
|--------|-------|
| test_coverage | 1.0 |
| code_quality | 1.0 |
| defect_rate | 1.0 |
| maintainability | 0.959 |
| idiomatic | 0.78 |
| token_efficiency | 0.005 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Uses H2 instead of SQLite — valid Java equivalent

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-7_tooling=none/rep2
cat stack.json
cat TASK.md
# Scores read from retort.db — no build/test re-run needed
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1) AND rr.metric_name IN ('test_coverage','code_quality','defect_rate','maintainability','idiomatic','token_efficiency');"
grep -cE "@Test" src/test/java/com/example/books/BookControllerTest.java
grep -rE "@Disabled|@Ignore" src/test/ --include="*.java"
```
