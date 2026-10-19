# Evaluation: rest-api-crud · java · hermes-0222 · ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ · neutral · tcap · rep 2

## Summary

- **Factors:** language=java, agent=hermes-0222, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, prompt=neutral, stack=tcap
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json) — 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookController.java:create` → `BookRepository.java:save` (INSERT with generated key) |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:list` → `findAll` (`SELECT ... ORDER BY id`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookController.java:list` dispatches to `BookRepository.java:findByAuthor` (`WHERE author = ? COLLATE NOCASE`) |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `BookController.java:get` → `findById` → `orElseThrow` 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookController.java:update` → `BookRepository.java:update` (404 if missing, then validate) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookController.java:delete` → `deleteById` (204, 404 if absent) |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `pom.xml` xerial sqlite-jdbc 3.50.3.0; `application.properties` `jdbc:sqlite:books.db`; `schema.sql` books DDL |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 404/400 via `GlobalExceptionHandler.java` JSON envelope |
| R9 | Validation: title and author required | ✓ implemented | `BookController.java:validate` → 400 when title/author blank; tests `createBookWithoutTitle/Author` |
| R10 | GET /health | ✓ implemented | `BookController.java:health` returns `{status:ok}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, `mvn spring-boot:run`, `mvn test`, API docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookApiIntegrationTest.java` — 14 `@Test` methods, test_coverage=1.0 |

## Build & Test

Build/test not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=1.0, code_quality=1.0, defect_rate=1.0,
             maintainability=0.9558, idiomatic=0.8, token_efficiency=0.0083
```

```text
Agent self-report (_agent_stdout.log): Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
test_coverage=1.0 ⇒ build compiled and every test passed.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~290 (5 Java classes + test + schema/props) |
| Files (excl. build artifacts) | 21 (incl. harness logs) |
| Dependencies | 4 Maven deps (spring-boot-starter-web, -jdbc, sqlite-jdbc, -test) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

None. All 12 pinned requirements implemented and exercised by tests; build and
tests pass; no skipped/disabled tests; lint clean (code_quality=1.0). Full-replace
PUT semantics (missing optional fields become null) are correct and intentional.

## Reproduce

```bash
cd "experiments/adrianco/experiment-89-thinkingcap-reach/rest-api-crud/runs/agent=hermes-0222_language=java_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap/rep2"
cat scores.json            # stored mechanical scores (build/test/lint)
grep -rE "@Test" src --include="*.java" | wc -l   # 14
grep -rE "@Disabled|@Ignore|assumeTrue" src --include="*.java" | wc -l   # 0
# optional full verification: mvn test
```
