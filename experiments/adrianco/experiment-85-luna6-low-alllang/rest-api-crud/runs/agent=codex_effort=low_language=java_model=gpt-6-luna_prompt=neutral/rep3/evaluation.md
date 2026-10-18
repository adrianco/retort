# Evaluation: rest-api-crud · agent=codex effort=low language=java model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=java, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=Spring Boot 3.3.5
- **Status:** failed — 1 of 4 tests fails (`test_coverage=0.75`); this is a REPAIR task whose stated goal was that all tests run and pass.
- **Requirements:** 12/12 implemented (code), 0 partial, 0 missing — but a test defect leaves one test red.
- **Tests:** 3 passed / 1 failed / 0 skipped (4 effective)
- **Build:** pass — clean compile (`defect_rate=1.0`, zero compiler diagnostics)
- **Lint:** pass — `code_quality=1.0`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 1 medium)

Scores read from `scores.json` (inline-gate archive; run not yet in `retort.db`):
`code_quality=1.0, test_coverage=0.75, defect_rate=1.0, maintainability=0.953, idiomatic=0.8, token_efficiency=0.0185`.
Per the Java scorer, `test_coverage` is the Surefire **pass rate**, so 0.75 = 3 of 4 tests passed; `defect_rate=1.0` is a clean `mvn compile` and does not reflect test outcomes.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookController.java:26-39` INSERT via GeneratedKeyHolder, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `BookController.java:41-45` `SELECT * FROM books ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookController.java:44` `WHERE lower(author)=lower(?)` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `BookController.java:47-48`, `find()` 404 at :67-71 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookController.java:50-55` (find→UPDATE→find) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookController.java:57-62` 204, 404 if 0 rows |
| R7 | SQLite / embedded DB | ✓ implemented | `pom.xml` xerial sqlite-jdbc; `application.properties:1` jdbc:sqlite |
| R8 | JSON + correct HTTP codes | ✓ implemented | 201/200/204/404 in controller; @NotBlank → 400 (Spring default) |
| R9 | Validation: title & author required | ✓ implemented | `BookRequest.java:5-6` `@NotBlank`; `@Valid` at `BookController.java:27,51` |
| R10 | GET /health | ✓ implemented | `BookController.java:64-65,73` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` run/test/API sections |
| R12 | ≥3 tests that run | ✓ implemented | `BookApiTest.java` 4 `@Test`, `test_coverage=0.75 > 0` |

All requirements are satisfied in the source. The failure is a **test defect**, not a
missing feature: the production code is correct, but the test suite asserts on a
hardcoded id that is not stable across methods (see Findings).

## Build & Test

Scores reused from `scores.json` — build/test not re-run (per skill). For context, the
agent's own `mvn test` attempts (see `_agent_stdout.log`) failed inside its sandbox for
**harness** reasons, not code: the user `~/.m2` cache was read-only (`Operation not
permitted`) and the `/tmp` fallback cache had no network to Maven Central. The agent did
fix a malformed JSON literal in the test (original compile error at `BookApiTest.java:[41,102]
illegal character: '\'`) before giving up on the test run. retort's scorer later ran the
suite in a working environment and recorded:

```text
mvn -q compile        → clean (defect_rate=1.0)
mvn -q test           → 3/4 passed (test_coverage=0.75)  # one id-dependent test fails
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java, source+test) | 156 |
| Files (excl. build artifacts) | 17 (6 Java/config source) |
| Dependencies (pom.xml) | 5 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build | clean compile |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] One of four tests fails — `clearDatabase()`'s `DELETE FROM books` does not reset
   SQLite's `AUTOINCREMENT` sequence in the shared in-memory DB, so the id-dependent test
   that runs second sees id≥2 and its `/books/1` assertions 404. `BookApiTest.java:22,29,33-36`.
2. [medium] Tests are coupled through one shared in-memory DB with no fixed method order;
   the outcome depends on JUnit's method ordering. `BookApiTest.java:15`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                      # code_quality/test_coverage/defect_rate/...
grep -nE "@Test" src/test/java/com/example/books/BookApiTest.java
# Build/test were NOT re-run; scores reused from scores.json per the evaluate-run skill.
```
