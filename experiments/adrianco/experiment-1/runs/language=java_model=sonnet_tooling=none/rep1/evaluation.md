# Evaluation: language=java_model=sonnet_tooling=none · rep 1

## Summary

- **Factors:** language=java, model=sonnet, tooling=none
- **Status:** failed (no Java source files generated — only scaffolding produced)
- **Requirements:** 1/12 implemented, 1 partial, 10 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** fail — no source code to compile (zero .java files in workspace)
- **Lint:** unavailable — no source code to lint
- **Architecture:** summary skill unavailable
- **Findings:** 12 items in `findings.jsonl` (1 critical, 11 high)
- **Stored scores (retort.db):** test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.97, idiomatic=0.82, token_efficiency=0.5 — these contradict the actual workspace state (no source code exists)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book | ✗ missing | No Java source files exist |
| R2 | GET /books lists all books | ✗ missing | No Java source files exist |
| R3 | GET /books supports ?author= filter | ✗ missing | No Java source files exist |
| R4 | GET /books/{id} returns single book | ✗ missing | No Java source files exist |
| R5 | PUT /books/{id} updates a book | ✗ missing | No Java source files exist |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No Java source files exist |
| R7 | Data stored in SQLite | ~ partial | pom.xml:38 has sqlite-jdbc dep; application.properties configures SQLiteDialect — but no entity/repository code |
| R8 | JSON responses with HTTP status codes | ✗ missing | No controller code exists |
| R9 | Input validation: title and author required | ✗ missing | pom.xml has validation dep but no annotations applied |
| R10 | GET /health health-check endpoint | ✗ missing | No controller code exists |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (98 lines) documents setup, build, API endpoints, and curl examples |
| R12 | At least 3 unit/integration tests | ✗ missing | No .java test files exist |

## Build & Test

```text
Build: FAIL — cannot compile; no Java source files present.
The workspace contains only:
  - pom.xml (61 lines, Spring Boot 3.2.3 with sqlite-jdbc, JPA, validation deps)
  - README.md (98 lines, comprehensive API documentation)
  - src/test/resources/application.properties (5 lines, SQLite in-memory config)
  - No src/main/java/ directory or any .java files

Note: retort.db reports test_coverage=1.0 for this run, which is inconsistent
with the archived workspace. The scores may have been computed against a
different workspace state or the scorer may treat missing source as a pass.
```

```text
Tests: NONE — zero .java files under src/test/.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (Java) |
| Lines of code (all files) | 164 (pom.xml + README.md + application.properties) |
| Files | 3 (deliverable files, excluding TASK.md/stack.json/_meta.json) |
| Dependencies | 6 (declared in pom.xml: spring-boot-starter-web, data-jpa, validation, sqlite-jdbc, hibernate-community-dialects, starter-test) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No Java source files in workspace — build cannot succeed
2. [high] POST /books endpoint missing — no controller code
3. [high] GET /books list endpoint missing
4. [high] GET /books ?author= filter missing
5. [high] GET /books/{id} endpoint missing

## Notes

The agent produced project scaffolding: a correct Maven pom.xml with appropriate Spring Boot dependencies (Web, JPA, Validation, SQLite), a well-written README.md documenting all required API endpoints with curl examples, and a test application.properties configuring SQLite. However, it failed to generate any actual Java source code — no controllers, models, repositories, services, or test classes. The README describes an API that was never implemented.

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=none/rep1/
find . -name "*.java"   # returns nothing
ls -R src/               # only test/resources/application.properties
cat pom.xml              # shows Spring Boot project with correct dependencies
```
