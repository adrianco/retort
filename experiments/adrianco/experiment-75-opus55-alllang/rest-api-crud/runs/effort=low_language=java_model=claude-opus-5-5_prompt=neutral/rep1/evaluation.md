# Evaluation: effort=low_language=java_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `Tests run: 4, Failures: 0, Errors: 0, Skipped: 0`
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.9556, maintainability=0.9068 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookServer.java:59,110` `create()` INSERT → 201 |
| R2 | GET /books lists books | ✓ implemented | `BookServer.java:58,146` `list()` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookServer.java:147` `WHERE author = ? COLLATE NOCASE`; test `listWithAuthorFilter` |
| R4 | GET /books/{id} single book | ✓ implemented | `BookServer.java:67` `find(id)`, 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookServer.java:68,125` `update()` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookServer.java:69-73` DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `pom.xml` sqlite-jdbc; `BookServer.java:21,179` `jdbc:sqlite:` |
| R8 | JSON responses + status codes | ✓ implemented | `BookServer.java:41-50` `handle()`; 201/200/204/400/404/405/500 |
| R9 | Validation: title & author required | ✓ implemented | `BookServer.java:92-102` `validate()`; test `validation` |
| R10 | GET /health | ✓ implemented | `BookServer.java:27-28` → `{"status":"ok"}`; test `health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, run, test, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | `BookServerTest.java` — 4 `@Test`, all pass |

## Build & Test

```text
mvn test  (from _agent_stdout.log)
Test set: books.BookServerTest
Tests run: 4, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.449 s
```

Scores read from `scores.json` (not re-run): test_coverage=1.0, defect_rate=1.0,
code_quality=0.9556, maintainability=0.9068, idiomatic=0.70.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 263 (183 main + 80 test) |
| Files | 2 Java (+ pom.xml, README.md) |
| Dependencies | 3 (sqlite-jdbc, jackson-databind, junit-jupiter) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | test suite 0.449s |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all info, no defects:

1. [info] GET /books ?author= is exact (case-insensitive) match only — satisfies R3.
2. [info] Single shared JDBC connection with synchronized routing serializes requests — correct at this scale.
3. [info] No pagination on GET /books — not required by spec.

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=java_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                     # stored mechanical scores (build+test already run)
grep -rc "@Test" src/test           # 4 tests
grep -rEn "@Disabled|assumeTrue|@Ignore" src/test | wc -l   # 0 skips
```
