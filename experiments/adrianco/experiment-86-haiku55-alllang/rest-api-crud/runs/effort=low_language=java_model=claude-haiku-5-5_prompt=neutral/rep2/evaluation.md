# Evaluation: effort=low language=java model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=java, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass (test_coverage=1.0 ⇒ `mvn test` built + ran all tests)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookServer.java:145-159` handleCreate → `BookRepository.create` INSERT with all four fields |
| R2 | GET /books lists all books | ✓ implemented | `BookServer.java:131-134` handleList → `BookRepository.findAll` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookServer.java:132` queryParam; `BookRepository.java:72-77` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `BookServer.java:136-143` handleGet returns 404 when empty |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookServer.java:161-178`; `BookRepository.java:95-104` UPDATE, 404 if no rows |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookServer.java:180-186`; `BookRepository.java:107-114` DELETE, 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `BookRepository.java:24-40` `jdbc:sqlite:`; pom sqlite-jdbc 3.46.0.0; reopen-persistence test `BookApiTest.java:182` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `BookServer.java:238-245` sendJson; 201/200/204/400/404/405/500/503 used throughout |
| R9 | Input validation: title and author required | ✓ implemented | `BookValidator.java:26-35` rejects blank title/author → 400 |
| R10 | GET /health health-check | ✓ implemented | `BookServer.java:123-129` handleHealth (DB ping) |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — build/test/run, env vars, endpoint table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookApiTest.java` — 13 `@Test`, 0 skipped, test_coverage=1.0 |

No requirements partial or missing. Enhancements beyond spec noted in findings (ISBN format validation, DB-backed health probe, reopen-persistence test).

## Build & Test

Mechanical scores read from `scores.json` (gate ran during `retort run`) — build/test not re-run per skill guidance.

```text
scores.json
test_coverage = 1.0   # mvn test built + all tests passed
code_quality  = 1.0   # lint/quality
defect_rate   = 1.0   # build+test succeeded
maintainability = 0.743
idiomatic     = 0.6
token_efficiency = 0.0297
```

```text
Tests: 13 @Test methods in BookApiTest.java
Skips: 0 (@Disabled/@Ignore/assume* = 0)
Effective tests: 13
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 510 |
| Lines of code (test) | 215 |
| Files (excl. build artifacts) | 16 |
| Dependencies (pom artifactIds incl. plugins) | 7 |
| Runtime deps | sqlite-jdbc, jackson-databind |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] ISBN-10/13 format validation beyond spec — `BookValidator.java:39-43`
2. [info] Health endpoint performs a real DB liveness probe — `BookServer.java:123-129`
3. [info] Persistence verified across repository reopen — `BookApiTest.java:182-196`

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=java_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # mechanical scores (do not re-run build/test)
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rE "@Test" src --include="*.java" | wc -l    # 13 tests
grep -rE "@Disabled|@Ignore|assume" src --include="*.java" | wc -l  # 0 skips
```
