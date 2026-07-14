# Evaluation: language=java_model=sonnet_tooling=beads · rep 2

## Summary

- **Factors:** language=java, model=sonnet, tooling=beads
- **Status:** failed (archive incomplete — no source code present)
- **Requirements:** 0/12 implemented, 1 partial, 11 missing
- **Tests:** cannot verify — no test source files in archive (retort.db test_coverage=1.0 suggests tests passed during live run)
- **Build:** cannot verify — no source code to build (retort.db defect_rate=1.0 suggests build succeeded during live run)
- **Lint:** unavailable
- **Architecture:** no source code to analyze
- **Findings:** 14 items in `findings.jsonl` (8 critical, 4 high, 1 medium, 1 info)

### Score Discrepancy Note

retort.db records test_coverage=1.0, code_quality=1.0, defect_rate=1.0 for this run, and the prior evaluation referenced specific Java files (BookController.java, Book.java, BookApiTest.java). The source code existed during the live run but is absent from the archived workspace. This evaluation reflects the current archive state.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book | ✗ missing | No .java source files in archive |
| R2 | GET /books lists all books | ✗ missing | No .java source files in archive |
| R3 | GET /books supports ?author= filter | ✗ missing | No .java source files in archive |
| R4 | GET /books/{id} returns single book | ✗ missing | No .java source files in archive |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .java source files in archive |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .java source files in archive |
| R7 | Data stored in SQLite | ✗ missing | pom.xml has sqlite-jdbc dep but no source to use it |
| R8 | JSON responses with HTTP status codes | ✗ missing | No .java source files in archive |
| R9 | Input validation: title and author required | ✗ missing | pom.xml has validation dep but no source to use it |
| R10 | GET /health health-check endpoint | ✗ missing | No .java source files in archive |
| R11 | README.md with setup and run instructions | ~ partial | README.md exists (75 lines) with setup/API docs, but describes absent code |
| R12 | At least 3 unit/integration tests | ✗ missing | No test source files in archive |

## Build & Test

```text
Build and test cannot be run — no Java source files exist in the archive.

retort.db stored scores (from live run):
  test_coverage  = 1.0  (all tests passed)
  code_quality   = 1.0
  defect_rate    = 1.0  (build+test succeeded)
  maintainability = 0.963
  idiomatic      = 0.68
  token_efficiency = 0.5
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (no .java files) |
| Files (excluding eval artifacts) | 8 |
| Dependencies (pom.xml) | 6 (Spring Boot Web, JDBC, Validation, SQLite JDBC, Hibernate Dialects, Spring Boot Test) |
| Tests total | 0 (in archive) |
| Tests effective | 0 (in archive) |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Archive missing all source code — only scaffolding present
2. [critical] POST /books — no source code in archive
3. [critical] GET /books — no source code in archive
4. [critical] GET /books/{id} — no source code in archive
5. [critical] PUT /books/{id} — no source code in archive

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=beads/rep2
ls -la           # Observe no src/ directory
find . -name "*.java"  # Returns no results
cat pom.xml      # Scaffolding exists but no source code
```
