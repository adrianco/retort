# Evaluation: language=java_model=sonnet_tooling=beads · rep 1

## Summary

- **Factors:** language=java, model=sonnet, tooling=beads
- **Status:** failed (Java source files missing from archive — 0 .java files committed)
- **Requirements:** 1/12 implemented, 1 partial, 10 missing
- **Tests:** 0 effective (0 test files in archive; test_coverage=1.0 from retort.db — see note)
- **Build:** unavailable (no source to compile); test_coverage=1.0 from retort.db
- **Lint:** unavailable (no source to lint); code_quality=1.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 13 items in `findings.jsonl` (7 critical, 3 high, 1 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✗ missing | 0 .java files in archive |
| R2 | GET /books lists all books | ✗ missing | 0 .java files in archive |
| R3 | GET /books supports ?author= filter | ✗ missing | 0 .java files in archive |
| R4 | GET /books/{id} returns a single book | ✗ missing | 0 .java files in archive |
| R5 | PUT /books/{id} updates a book | ✗ missing | 0 .java files in archive |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | 0 .java files in archive |
| R7 | Data stored in SQLite/embedded DB | ~ partial | pom.xml:39 sqlite-jdbc dep; application.properties configures jdbc:sqlite — no @Entity or @Repository |
| R8 | JSON responses with HTTP status codes | ✗ missing | No @RestController class |
| R9 | Input validation: title and author required | ✗ missing | pom.xml:35 has validation starter but no .java code |
| R10 | GET /health health-check endpoint | ✗ missing | No controller in archive |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents setup, run, endpoints, and test instructions |
| R12 | At least 3 unit/integration tests | ✗ missing | 0 test files; only src/test/resources/application.properties |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run per skill policy):
  test_coverage   = 1.0
  code_quality    = 1.0
  defect_rate     = 1.0
  idiomatic       = 0.82
  maintainability = 0.97
  token_efficiency = 0.5
```

**Note on score validity:** _meta.json records `succeeded: true` and retort.db
shows test_coverage=1.0, indicating the agent's code built and tests passed at
scoring time. However, the Java source and test files were never committed to
git — the archive contains only scaffolding (pom.xml, README.md,
application.properties). The stored scores reflect code that existed transiently
but is no longer recoverable from this archive.

```text
Test files found:  0
Tests passed:      0
Tests failed:      0
Tests skipped:     0
Effective tests:   0
Skip ratio:        0.0%
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java source) | 0 |
| Lines of config/build | 66 (pom.xml 61 + application.properties 5) |
| Files (deliverable, excl. evaluation outputs) | 3 (pom.xml, README.md, application.properties) |
| Dependencies (Maven) | 6 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] archive-incomplete — Java source and test files missing from archive — 0 .java files committed
2. [critical] R1 — POST /books — no source code in archive
3. [critical] R2 — GET /books — no source code in archive
4. [critical] R4 — GET /books/{id} — no source code in archive
5. [critical] R5 — PUT /books/{id} — no source code in archive

Additional critical: R6 (DELETE), R8 (JSON responses), R12 (no tests).
High: R3 (?author= filter), R9 (validation), R10 (/health).
Medium: R7 (SQLite partial — config only).

## Notes

This run produced project scaffolding only: a Maven pom.xml with correct Spring Boot
3.2.4 and SQLite dependencies, a comprehensive README documenting all endpoints, and
a test application.properties for in-memory SQLite. The agent failed to commit any
Java source files to git — no controllers, entities, repositories, services, or test
classes exist in the archive.

The retort.db scores (test_coverage=1.0, defect_rate=1.0) and _meta.json
(succeeded: true) suggest the agent did produce working code that built and passed
tests, but the source files were not included in the git commit. This is likely an
archival issue with the beads-tooling workflow rather than a code-generation failure.

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=beads/rep1
find . -name "*.java"                           # confirms 0 Java files
git ls-files -- src/                            # only application.properties
cat pom.xml                                     # Spring Boot + SQLite deps present
cat README.md                                   # documents endpoints that don't exist in archive
cat _meta.json                                  # succeeded: true
```
