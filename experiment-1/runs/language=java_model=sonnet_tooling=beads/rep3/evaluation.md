# Evaluation: language=java_model=sonnet_tooling=beads · rep 3

## Summary

- **Factors:** language=java, model=sonnet, tooling=beads
- **Status:** failed (no Java source code generated — only pom.xml and README.md scaffolding exist)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** pass (vacuous — test_coverage=1.0 from retort.db, but no source to compile or tests to run)
- **Lint:** unavailable — no source files to lint
- **Architecture:** summary skill not invoked — no source code to analyze
- **Findings:** 12 items in `findings.jsonl` (1 critical, 11 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book | ✗ missing | No Java source files in workspace |
| R2 | GET /books lists all books | ✗ missing | No Java source files in workspace |
| R3 | GET /books supports ?author= filter | ✗ missing | No Java source files in workspace |
| R4 | GET /books/{id} returns single book | ✗ missing | No Java source files in workspace |
| R5 | PUT /books/{id} updates a book | ✗ missing | No Java source files in workspace |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No Java source files in workspace |
| R7 | Data stored in SQLite | ✗ missing | pom.xml has sqlite-jdbc dep but no entity/repo/config |
| R8 | JSON responses with HTTP status codes | ✗ missing | No controllers exist |
| R9 | Input validation: title and author required | ✗ missing | pom.xml has validation starter but no Java code uses it |
| R10 | GET /health health-check endpoint | ✗ missing | No Java source files in workspace |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 78 lines, documents all endpoints, build, run, and test commands |
| R12 | At least 3 unit/integration tests | ✗ missing | No test files exist |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run per skill policy):
  test_coverage  = 1.0
  code_quality   = 1.0
  defect_rate    = 1.0
  idiomatic      = 0.88
  maintainability = 0.97
  token_efficiency = 0.5

Note: test_coverage=1.0 is vacuous — with 0 source files and 0 tests,
Maven reports 0 failures. This does NOT indicate a working implementation.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (Java) |
| Lines of code (scaffolding) | 144 (pom.xml: 66, README.md: 78) |
| Files | 8 (all scaffolding/meta — no source) |
| Dependencies (pom.xml) | 7 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A (score from DB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No Java source code generated — entire src/ directory is missing
2. [high] POST /books endpoint not implemented (R1)
3. [high] GET /books list endpoint not implemented (R2)
4. [high] GET /books ?author= filter not implemented (R3)
5. [high] GET /books/{id} endpoint not implemented (R4)

… plus 7 more high-severity findings (R5–R10, R12).

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=beads/rep3

# Verify no source code
find . -name "*.java" | wc -l   # → 0
ls -la                           # only pom.xml, README.md, scaffolding

# Scores were read from retort.db:
sqlite3 -readonly ../../retort.db "
  SELECT rr.metric_name, rr.value
  FROM run_results rr
  WHERE rr.run_id = (
    SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'$.language')='java'
      AND json_extract(er.run_config_json,'$.model')='sonnet'
      AND json_extract(er.run_config_json,'$.tooling')='beads'
      AND er.replicate=3 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
```
