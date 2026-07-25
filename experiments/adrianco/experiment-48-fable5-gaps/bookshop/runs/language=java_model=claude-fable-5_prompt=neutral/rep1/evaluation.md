# Evaluation: language=java_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-fable-5, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (test gate compiled + ran; `test_coverage=1.0`, `defect_rate=1.0`)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** summary skill unavailable in this session; see notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean, idiomatic Javalin + SQLite implementation. Every pinned requirement is
satisfied with concrete evidence, tests execute and pass, and there are no skipped
tests. No defects at or above `info` severity.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `App.java:27` → `BookDao.create` (`BookDao.java:33`), returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `App.java:35` → `BookDao.findAll` (`BookDao.java:54`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `App.java:36` reads `author` param; `BookDao.java:56` adds `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `App.java:40`; 404 via `notFound` (`App.java:125`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `App.java:53` → `BookDao.update` (`BookDao.java:84`) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `App.java:70` → `BookDao.delete` (`BookDao.java:100`), 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `App.java:132` `jdbc:sqlite:`; `BookDao` uses JDBC + `CREATE TABLE` (`BookDao.java:22`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across `App.java` (e.g. :32, :76, :108, :126, :83) |
| R9 | Input validation: title and author required | ✓ implemented | `readValidBook` (`App.java:100-110`) returns 400 with details |
| R10 | GET /health health-check | ✓ implemented | `App.java:25` returns `{"status":"ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents build/test/run + endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 `@Test` methods in `BookApiTest.java`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 1.0   → build compiled + all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 1.0   → lint/quality clean
```

Test suite (`BookApiTest.java`) spins up Javalin on an ephemeral port against an
in-memory SQLite DB and exercises the API over real HTTP: health, create+fetch,
validation rejects (missing fields + malformed JSON), author filter, update+validate,
delete, and missing/bad-id error paths.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java, src incl. tests) | 467 |
| Files (excl. target/.git) | 14 |
| Dependencies (`<artifactId>` in pom.xml) | 8 |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (read from stored scores) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `medium`:

1. [info] 8 tests provided — exceeds the 3-test minimum
2. [info] Robust error handling beyond spec (SQLException→500, non-numeric id→400, malformed JSON→400)

## Reproduce

```bash
cd runs/language=java_model=claude-fable-5_prompt=neutral/rep1
cat scores.json          # stored mechanical scores (build/test/lint)
grep -rE "@Test" src --include="*.java" | wc -l   # 8
grep -rE "@Disabled|@Ignore|assumeTrue" src --include="*.java" | wc -l  # 0
# Optional full re-run (slow, JVM):
mvn test
```
