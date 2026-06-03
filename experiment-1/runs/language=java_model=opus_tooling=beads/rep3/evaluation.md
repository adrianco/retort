# Evaluation: language=java_model=opus_tooling=beads · rep 3

## Summary

- **Factors:** language=java, model=opus, tooling=beads
- **Status:** failed (no Java source code — entire implementation missing)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** unavailable — no source files to compile
- **Lint:** unavailable — no source files to lint
- **Architecture:** no source code to analyze; summary skill not applicable
- **Findings:** 12 items in `findings.jsonl` (1 critical, 11 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✗ missing | no src/ directory; zero .java files |
| R2 | GET /books lists all books | ✗ missing | no src/ directory; zero .java files |
| R3 | GET /books supports ?author= filter | ✗ missing | no src/ directory; zero .java files |
| R4 | GET /books/{id} returns a single book | ✗ missing | no src/ directory; zero .java files |
| R5 | PUT /books/{id} updates a book | ✗ missing | no src/ directory; zero .java files |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | no src/ directory; zero .java files |
| R7 | Data stored in SQLite | ✗ missing | sqlite-jdbc in pom.xml:29 but no code uses it |
| R8 | JSON responses with HTTP status codes | ✗ missing | no src/ directory; zero .java files |
| R9 | Input validation: title and author required | ✗ missing | no src/ directory; zero .java files |
| R10 | GET /health health-check endpoint | ✗ missing | no src/ directory; zero .java files |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents build, run, endpoints, status codes |
| R12 | At least 3 unit/integration tests | ✗ missing | no src/test/ directory; zero test files |

## Build & Test

```text
No build or test execution possible — zero Java source files exist in the workspace.
The agent created pom.xml (Maven build config) and README.md but never generated
any src/main/java/ or src/test/java/ directories or .java files.
```

Note: retort.db reports test_coverage=1.0, code_quality=1.0, defect_rate=1.0 for this run.
These scores are misleading — the scorers returned perfect scores because there was nothing
to fail, not because the implementation is correct.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java source) | 0 |
| Lines of code (all files) | 300 (pom.xml, README, config) |
| Files | 9 |
| Dependencies (pom.xml) | 5 (javalin, jackson, sqlite-jdbc, slf4j, junit) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No Java source code in workspace — entire implementation missing
2. [high] POST /books endpoint not implemented
3. [high] GET /books list endpoint not implemented
4. [high] GET /books ?author= filter not implemented
5. [high] GET /books/{id} endpoint not implemented

## Reproduce

```bash
cd experiment-1/runs/language=java_model=opus_tooling=beads/rep3
find . -name "*.java"                          # confirms zero source files
find . -type f | sort                          # lists all 9 files
cat stack.json                                 # {"language": "java", ...}
cat pom.xml                                    # build config exists but nothing to build
```
