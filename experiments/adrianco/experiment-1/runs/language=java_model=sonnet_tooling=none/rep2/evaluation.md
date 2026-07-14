# Evaluation: language=java_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=java, model=sonnet, tooling=none
- **Status:** failed (agent generated only pom.xml and README.md — no Java source code)
- **Requirements:** 0/12 implemented, 0 partial, 12 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** pass (vacuous — no source to compile; test_coverage=1.0 from retort.db)
- **Lint:** pass (vacuous — code_quality=1.0 from retort.db; no source to lint)
- **Architecture:** no source code to analyze; summary skill not applicable
- **Findings:** 13 items in `findings.jsonl` (8 critical, 3 high, 0 medium, 1 low, 0 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✗ missing | No src/ directory; no .java files |
| R2 | GET /books lists all books | ✗ missing | No src/ directory; no controller class |
| R3 | GET /books ?author= filter | ✗ missing | No src/ directory; no query param handling |
| R4 | GET /books/{id} returns single book | ✗ missing | No src/ directory; no controller class |
| R5 | PUT /books/{id} updates a book | ✗ missing | No src/ directory; no controller class |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No src/ directory; no controller class |
| R7 | Data stored in SQLite | ✗ missing | pom.xml:39 has sqlite-jdbc dep but no entity/repo/config classes |
| R8 | JSON responses with HTTP status codes | ✗ missing | No controller classes exist |
| R9 | Input validation (title, author required) | ✗ missing | pom.xml:36 has validation dep but no annotations exist |
| R10 | GET /health health-check endpoint | ✗ missing | No health controller or actuator config |
| R11 | README.md with setup/run instructions | ✗ missing | README.md exists and is well-written but describes non-existent code |
| R12 | At least 3 unit/integration tests | ✗ missing | No src/test/ directory; 0 test files |

## Build & Test

```text
Build/test scores from retort.db:
  test_coverage  = 1.0  (vacuous — no tests to fail)
  code_quality   = 1.0  (vacuous — no source to lint)
  defect_rate    = 1.0
  idiomatic      = 0.86
  maintainability = 0.95
  token_efficiency = 0.5
```

Note: test_coverage=1.0 is misleading — the Maven project has no source or test
files, so `mvn test` succeeds vacuously (nothing to compile, nothing to fail).
This is a scoring artifact, not evidence of working code.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (Java) |
| Lines of config (pom.xml) | 61 |
| Lines of docs (README.md) | 78 |
| Files | 5 (TASK.md, stack.json, _meta.json, pom.xml, README.md) |
| Dependencies (pom.xml) | 6 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A (no build attempted — stored scores used) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] POST /books endpoint missing — no Java source files exist
2. [critical] GET /books/{id} endpoint missing — no Java source files exist
3. [critical] PUT /books/{id} endpoint missing — no Java source files exist
4. [critical] DELETE /books/{id} endpoint missing — no Java source files exist
5. [critical] SQLite data storage missing — no persistence code

## Reproduce

```bash
cd experiment-1/runs/language=java_model=sonnet_tooling=none/rep2
# Verify no source files
find . -name "*.java" | wc -l   # → 0
# Check stored scores
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='sonnet' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
