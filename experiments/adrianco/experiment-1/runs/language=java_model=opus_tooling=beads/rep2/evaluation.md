# Evaluation: language=java_model=opus_tooling=beads · rep 2

## Summary

- **Factors:** language=java, model=opus, tooling=beads
- **Status:** cannot-verify (Java source files missing from archive — likely archival issue, not agent failure)
- **Requirements:** 1/12 implemented, 1 partial, 10 missing (cannot verify from archive)
- **Tests:** 0 verifiable (0 .java test files in archive); retort.db test_coverage=1.0 suggests tests passed at scoring time
- **Build:** cannot-verify — no source in archive; retort.db defect_rate=1.0 indicates build succeeded at scoring time
- **Lint:** unavailable — no source to lint
- **Architecture:** summary skill unavailable — no source to analyze
- **Findings:** 13 items in `findings.jsonl` (1 critical, 10 high, 1 medium, 1 info)

**Note:** retort.db scores (test_coverage=1.0, code_quality=1.0, defect_rate=1.0, idiomatic=0.75, maintainability=0.97, token_efficiency=0.5) indicate the agent produced a functional implementation that was scored successfully. The Java source files are absent from the archived workspace — likely an archival issue rather than an agent failure.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✗ missing | No .java files in archive |
| R2 | GET /books lists all books | ✗ missing | No .java files in archive |
| R3 | GET /books ?author= filter | ✗ missing | No .java files in archive |
| R4 | GET /books/{id} single book | ✗ missing | No .java files in archive |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .java files in archive |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .java files in archive |
| R7 | Data stored in SQLite | ~ partial | `pom.xml:37` sqlite-jdbc dep + `application.properties` SQLiteDialect config, but no entity/repo code |
| R8 | JSON responses with HTTP status codes | ✗ missing | No controller code in archive |
| R9 | Input validation: title and author required | ✗ missing | `pom.xml:31` validation starter present but no annotations verifiable |
| R10 | GET /health health-check endpoint | ✗ missing | No controller code in archive |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents JDK/Maven requirements, build/run commands, endpoints, and curl examples |
| R12 | At least 3 unit/integration tests | ✗ missing | `src/test/java/` absent; only `src/test/resources/application.properties` |

## Build & Test

```text
Build/test not re-run (stored scores used per policy).
retort.db scores for this run:
  test_coverage    = 1.0   (build + all tests passed at scoring time)
  code_quality     = 1.0
  defect_rate      = 1.0
  maintainability  = 0.9669
  idiomatic        = 0.75
  token_efficiency = 0.5

Archive state: 0 .java files present — source not available for verification.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java source) | 0 (absent from archive) |
| Lines of code (scaffolding) | 122 (pom.xml: 58, README.md: 59, application.properties: 5) |
| Files (workspace, excl. eval artifacts) | 9 |
| Dependencies (Maven) | 6 |
| Tests total | 0 verifiable in archive |
| Tests effective | 0 verifiable in archive |
| Skip ratio | N/A |
| Build duration | N/A (not re-run) |
| Skipped tests | 0 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[critical]** Java source files missing from archive — zero .java files in workspace
2. **[high]** POST /books — cannot verify, source files absent from archive
3. **[high]** GET /books list — cannot verify, source files absent from archive
4. **[high]** GET /books ?author= filter — cannot verify, source files absent
5. **[high]** GET /books/{id} — cannot verify, source files absent from archive

## Reproduce

```bash
cd experiment-1/runs/language=java_model=opus_tooling=beads/rep2
find . -name '*.java'                    # confirms 0 Java files
cat stack.json                           # {"language": "java", ...}
cat _meta.json                           # {"replicate": 2, "succeeded": true}
sqlite3 -readonly ../../retort.db "
  SELECT rr.metric_name, rr.value
  FROM run_results rr
  WHERE rr.run_id = (
      SELECT er.id FROM experiment_runs er
      WHERE json_extract(er.run_config_json,'$.language')='java'
        AND json_extract(er.run_config_json,'$.model')='opus'
        AND json_extract(er.run_config_json,'$.tooling')='beads'
        AND er.replicate=2 AND er.status='completed'
      ORDER BY er.finished_at DESC LIMIT 1);"
```
