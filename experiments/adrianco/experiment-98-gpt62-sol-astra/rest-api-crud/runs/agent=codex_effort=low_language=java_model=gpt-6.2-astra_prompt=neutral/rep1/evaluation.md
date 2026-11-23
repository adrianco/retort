# Evaluation: rest-api-crud · agent=codex effort=low language=java model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `scores.json` test_coverage=1.0 (build + tests ran green)
- **Lint:** pass — code_quality=0.956 from `scores.json`
- **Architecture:** single-file JDK `com.sun.net.httpserver` service over SQLite JDBC; see notes below (run-summary skill not invoked — no separate summary generated)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored scores (`scores.json`): test_coverage=1.0, defect_rate=1.0, code_quality=0.956, idiomatic=0.72, maintainability=0.243, token_efficiency=0.0178. The retort.db row is not yet present (inline gate run); `scores.json` is authoritative.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookApi.java:94-106` INSERT … RETURNING *, 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `BookApi.java:70-80` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `BookApi.java:71-72,120-129` `authorFilter` + `WHERE author=?` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `BookApi.java:111-116` returns 200/404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookApi.java:94-106` UPDATE … RETURNING, 404 if no row |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookApi.java:110-113` 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `BookApi.java:18-20` `jdbc:sqlite:`; `pom.xml:6` sqlite-jdbc 3.50.3.0 |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `BookApi.java:32-39` JSON writer; 201/200/204/400/404/405/500 |
| R9 | Validation: title & author required | ✓ implemented | `BookApi.java:87-88` rejects blank/non-string → 400; test `rejectsInvalidInput` |
| R10 | GET /health | ✓ implemented | `BookApi.java:68` returns 200 `{"status":"ok"}`; test `healthAndMissingResources` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md:1-29` JDK/Maven setup, run, curl, endpoint table |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `BookApiTest.java` 4 `@Test` methods; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per skill (compiled/JVM re-run is the slow, duplicated step).

```text
scores.json: test_coverage=1.0  → mvn package (build + surefire) ran green
             code_quality=0.956 → lint/quality signal
             defect_rate=1.0    → build + tests succeeded
```

Tests exercise the full CRUD lifecycle, list + author filter, input validation (malformed JSON, empty object, blank title, non-integer year, missing author), health, and 404/405 paths — all through `BookApi.handle(...)` against a real temp SQLite DB (`@TempDir`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 201 (BookApi 141 + BookApiTest 60) |
| Files (source) | 4 (BookApi.java, BookApiTest.java, pom.xml, README.md) |
| Dependencies | 3 (sqlite-jdbc, jackson-databind, junit-jupiter) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] GET /books has no pagination — not required by spec (`BookApi.java:70-80`)
2. [info] PUT /books/{id} is full-replace, nulling omitted optional fields — documented intentional behavior (`README.md:29`)

No correctness, build, test, or security defects found. All requirements implemented and tested.

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6.2-astra_prompt=neutral/rep1
cat scores.json                                   # stored build/test/lint scores
grep -rEn "@Disabled|assumeTrue|@Ignore" . --include="*.java" | wc -l   # 0 skips
grep -rEc "@Test" BookApiTest.java                # 4 tests
# optional re-run: mvn test
```
