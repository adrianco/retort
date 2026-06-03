# Evaluation: language=java_model=opus_tooling=none · rep 3

## Summary

- **Factors:** language=java, model=opus, tooling=none
- **Status:** failed (no Java source files produced — agent generated only project scaffolding)
- **Requirements:** 1/12 implemented, 1 partial, 10 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** unavailable — no source files to compile
- **Lint:** unavailable — no source files to lint
- **Architecture:** no source code to analyze; summary skill not applicable
- **Findings:** 12 items in `findings.jsonl` (1 critical, 10 high, 1 medium)

**Stored scores (retort.db):** test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.967, idiomatic=0.67, token_efficiency=0.5. These scores are contradicted by the workspace state — the archive contains no Java source files, so tests could not have meaningfully passed. The scorer likely saw an empty test suite (0 tests = 0 failures = "pass").

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✗ missing | No .java files in src/ |
| R2 | GET /books lists all books | ✗ missing | No .java files in src/ |
| R3 | GET /books ?author= filter | ✗ missing | No .java files in src/ |
| R4 | GET /books/{id} returns single book | ✗ missing | No .java files in src/ |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .java files in src/ |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .java files in src/ |
| R7 | Data stored in SQLite | ~ partial | pom.xml has sqlite-jdbc dep; application.properties configures it; no @Entity/@Repository |
| R8 | JSON responses with HTTP status codes | ✗ missing | No controllers exist |
| R9 | Input validation (title, author required) | ✗ missing | No validation code |
| R10 | GET /health endpoint | ✗ missing | No health controller |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — documents setup, run, test, and endpoints |
| R12 | At least 3 unit/integration tests | ✗ missing | No test .java files; only src/test/resources/application.properties |

## Build & Test

```text
No Java source files exist in the workspace.
The agent produced only project scaffolding:
  - pom.xml (Spring Boot 3.4.1 + SQLite + JPA + validation dependencies)
  - README.md (setup and run instructions)
  - .gitignore (target/, *.db, IDE files)
  - src/test/resources/application.properties (SQLite in-memory config)

Build and test cannot be run — there is nothing to compile.
```

```text
Stored test_coverage=1.0 from retort.db is misleading:
with zero test classes, Maven reports 0 tests run / 0 failures,
which the scorer interprets as a passing suite.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java source) | 0 |
| Lines total (XML + MD + properties) | 113 |
| Files | 7 |
| Dependencies (pom.xml) | 6 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No Java source files produced — agent generated only project scaffolding
2. [high] R1: POST /books endpoint missing — no controller code
3. [high] R2: GET /books list endpoint missing — no controller code
4. [high] R3: GET /books ?author= filter missing — no controller code
5. [high] R4: GET /books/{id} endpoint missing — no controller code

## Reproduce

```bash
cd experiment-1/runs/language=java_model=opus_tooling=none/rep3
find . -name "*.java"                # confirms zero Java source files
find src -type f                      # shows only src/test/resources/application.properties
cat pom.xml                           # Spring Boot project skeleton present
cat README.md                         # documentation present
```
