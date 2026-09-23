# Evaluation: java · claude-opus-5-5 · neutral · effort=low · rep 3

## Summary

- **Factors:** language=java, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (`test_coverage=1.0` ⇒ compile + tests succeeded; not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `App.java:40-43` → `BookRepository.create`; `Book` record has all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `App.java:39` → `BookRepository.list:30` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `App.java:39` reads `author`; `BookRepository.list:31` `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `App.java:52` → `repo.get`, `.orElse(notFound)` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `App.java:53-55` → `BookRepository.update:47` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `App.java:57` → `BookRepository.delete:56`; 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository:14` CREATE TABLE; `jdbc:sqlite:`; sqlite-jdbc dep in pom.xml |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `App.java:87-97 handle()` writes JSON; 200/201/204/400/404/405/500 |
| R9 | Input validation: title & author required | ✓ implemented | `App.java:68-71`; test `validation()` `AppTest.java:58` |
| R10 | GET /health | ✓ implemented | `App.java:20-21` returns `{status:ok}`; test `health()` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — Run/Test/Endpoints sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 4 `@Test` methods in `AppTest.java`; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (produced by retort's scorers during the run):

```text
scores.json: test_coverage=1.0, code_quality=1.0, defect_rate=1.0,
             maintainability=0.894, idiomatic=0.7, token_efficiency=0.0199
```

`test_coverage=1.0` ⇒ `mvn test` compiled and all tests passed. No skipped/disabled tests
(`grep -Ec "@Disabled|@Ignore|assumeTrue" src/test` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 259 (App 106, BookRepository 77, AppTest 76) |
| Files | 3 source files |
| Dependencies | 3 (sqlite-jdbc, jackson-databind, junit-jupiter) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not re-run (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Returns 405 for unsupported methods on known paths — beyond the minimal spec.
2. [info] New JDBC connection opened per request; no connection pooling — acceptable at this scale.

No critical/high/medium/low findings: the run fully conforms to the spec and passes the build+test gate.

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=java_model=claude-opus-5-5_prompt=neutral/rep3
cat scores.json                                   # mechanical scores (build/test/lint)
grep -Ec "@Disabled|@Ignore|assumeTrue" src/test  # skipped-test count → 0
grep -rc "@Test" src/test/java/books/AppTest.java # test count → 4
find src -name '*.java' -exec wc -l {} +          # LOC
# (optional full re-run) mvn test
```
