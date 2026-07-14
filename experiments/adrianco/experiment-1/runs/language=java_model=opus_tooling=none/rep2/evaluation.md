# Evaluation: language=java_model=opus_tooling=none · rep 2

## Summary

- **Factors:** language=java, model=opus, tooling=none
- **Status:** cannot-verify (archive incomplete — no Java source files present; only pom.xml and README.md were archived)
- **Requirements:** 1/12 implemented, 2 partial, 9 missing (source absent from archive)
- **Tests:** unknown — no test source in archive (retort.db test_coverage=1.0 suggests 5 tests passed at run time)
- **Build:** unavailable — no source files to build
- **Lint:** unavailable — no source files to lint
- **Architecture:** summary skill unavailable (no source to analyze)
- **Findings:** 12 items in `findings.jsonl` (1 critical, 9 high, 2 medium)

> **Note:** retort.db scores (test_coverage=1.0, code_quality=1.0, defect_rate=1.0) indicate this run was fully functional at execution time. The archive appears to have failed to capture the `src/` directory. All `cannot-verify` / `missing` classifications below reflect the state of the **archive**, not necessarily the agent's output.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✗ missing | No .java files in archive |
| R2 | GET /books lists all books | ✗ missing | No .java files in archive |
| R3 | GET /books ?author= filter | ✗ missing | No .java files in archive |
| R4 | GET /books/{id} single book | ✗ missing | No .java files in archive |
| R5 | PUT /books/{id} update | ✗ missing | No .java files in archive |
| R6 | DELETE /books/{id} delete | ✗ missing | No .java files in archive |
| R7 | SQLite embedded DB storage | ~ partial | `pom.xml:31` sqlite-jdbc dependency; no source to verify usage |
| R8 | JSON responses + HTTP status codes | ✗ missing | No .java files in archive |
| R9 | Input validation (title/author) | ✗ missing | No .java files in archive |
| R10 | GET /health endpoint | ✗ missing | No .java files in archive |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — documents build, run, endpoints, and examples |
| R12 | At least 3 tests | ~ partial | `pom.xml:43` junit-jupiter dep + retort.db test_coverage=1.0; no test source in archive |

## Build & Test

No source files present in the archive. Cannot build or test.

retort.db stored scores (computed at run time):
```text
test_coverage    = 1.0   (build + all tests passed)
code_quality     = 1.0
defect_rate      = 1.0
maintainability  = 0.92
idiomatic        = 0.60
token_efficiency = 0.50
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (no .java files in archive) |
| Files (deliverables) | 2 (pom.xml, README.md) |
| Dependencies | 5 (javalin, jackson-databind, sqlite-jdbc, slf4j-simple, junit-jupiter) |
| Tests total | unknown (no test source in archive) |
| Tests effective | unknown |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Archive missing all Java source files — no src/ directory
2. [high] R1: POST /books — source absent from archive
3. [high] R2: GET /books list all — source absent from archive
4. [high] R3: GET /books ?author= filter — source absent from archive
5. [high] R4: GET /books/{id} — source absent from archive

## Reproduce

```bash
cd experiment-1/runs/language=java_model=opus_tooling=none/rep2/
find . -type f  # observe no .java files
cat pom.xml     # build config present
cat README.md   # documentation present
```
