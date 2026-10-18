# Evaluation: effort=low language=java model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=java, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass (not re-run; `test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (fixed denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookServer.java:121 createBook` → `BookRepository.java:38 insert`; test `createThenGetBookById` |
| R2 | GET /books lists all books | ✓ implemented | `BookServer.java:116 listBooks` → `BookRepository.java:64 findAll`; test `listFiltersByAuthorCaseInsensitively` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookRepository.java:66 WHERE LOWER(author)=LOWER(?)`; test asserts 2 of 3 returned |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `BookServer.java:128 getBook`, `:130` sends 404; test `unknownBookAndBadIdsReturnErrors` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookServer.java:137 updateBook` → `BookRepository.java:84 update`; tests `updateReplacesBook`, `updateValidatesInputAndMissingBooks` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookServer.java:147 deleteBook` → `BookRepository.java:96 delete`; test `deleteRemovesBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `BookRepository.java:24 DriverManager jdbc:sqlite`, CREATE TABLE books; sqlite-jdbc in pom.xml |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `BookServer.java:213 sendJson`; 201/200/204/400/404/405/500 throughout |
| R9 | Input validation: title and author required | ✓ implemented | `BookValidator.java:34-44`; test `createRejectsMissingTitleAndAuthor` (400) |
| R10 | GET /health health check | ✓ implemented | `BookServer.java:87` → 200 `{status:ok}`; test `healthEndpointReportsOk` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — build/test/run, env vars, data model, endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookApiTest.java` — 12 @Test methods, `test_coverage=1.0` |

No `prompt`-factor requirements (prompt=neutral is the standard instruction, not an extra checklist file).

## Build & Test

Not re-run — stored mechanical scores stand in (per evaluate-run skill step 2):

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0
             maintainability=0.7105  idiomatic=0.85  token_efficiency=0.0388
```

`test_coverage=1.0` ⇒ `mvn test` built the project and all tests passed.
`code_quality=1.0` ⇒ no lint/quality deductions.

## Metrics

| Metric | Value |
|--------|-------|
| Source files | 7 (6 main + 1 test) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Dependencies | 3 (jackson-databind, sqlite-jdbc, junit-jupiter) |
| Build | pass (stored) |
| Lint | pass (code_quality=1.0) |

## Findings

All info-level (enhancements beyond spec — no deductions):

1. [info] ISBN-10/13 check-digit validation beyond spec
2. [info] Edge-case HTTP handling (405, 400 on bad id, Location header, trailing-slash normalization)
3. [info] 12 tests across HTTP/repository/validator layers (spec required 3)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=java_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                       # stored mechanical scores (no re-run)
grep -rE "@Test" src/test | wc -l     # 12 tests
grep -rE "@Disabled|@Ignore|assumeTrue|assumeFalse" src/test | wc -l   # 0 skips
# Optional full rebuild (slow): mvn test
```
