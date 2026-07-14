# Evaluation: language=clojure_model=sonnet_tooling=none · rep 1

## Summary

- **Factors:** language=clojure, model=sonnet, tooling=none
- **Status:** failed (no source code generated — agent produced only project scaffolding)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** fail — no source code to build (test_coverage=0.0 from retort.db)
- **Lint:** unavailable — no source files to lint
- **Architecture:** no implementation to analyze; summary skill not invoked
- **Findings:** 12 items in `findings.jsonl` (1 critical, 11 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book | ✗ missing | No .clj source files in workspace |
| R2 | GET /books lists all books | ✗ missing | No .clj source files in workspace |
| R3 | GET /books ?author= filter | ✗ missing | No .clj source files in workspace |
| R4 | GET /books/{id} returns single book | ✗ missing | No .clj source files in workspace |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .clj source files in workspace |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .clj source files in workspace |
| R7 | SQLite embedded DB storage | ✗ missing | deps.edn lists next.jdbc/sqlite-jdbc but no code uses them |
| R8 | JSON responses + HTTP status codes | ✗ missing | deps.edn lists ring-json/cheshire but no code uses them |
| R9 | Input validation (title, author required) | ✗ missing | No .clj source files in workspace |
| R10 | GET /health endpoint | ✗ missing | No .clj source files in workspace |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — 96 lines, documents setup, run, and API endpoints |
| R12 | At least 3 unit/integration tests | ✗ missing | No test files; test_coverage=0.0 from retort.db |

## Build & Test

```text
Build: not re-run (test_coverage=0.0 from retort.db)
No .clj source files exist — the agent generated only project scaffolding:
  deps.edn (project dependencies)
  tests.edn (kaocha test runner config)
  README.md (documentation)
No src/ or test/ directories were created.
```

```text
Tests: not re-run (test_coverage=0.0 from retort.db)
No test files exist. 0 tests total, 0 effective.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Files (generated, excl. retort metadata) | 3 |
| Dependencies | 8 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No Clojure source code generated — build cannot succeed
2. [high] POST /books not implemented (R1)
3. [high] GET /books list not implemented (R2)
4. [high] GET /books ?author= filter not implemented (R3)
5. [high] GET /books/{id} not implemented (R4)

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=none/rep1
# Verify no source files
find . -name "*.clj" -o -name "*.cljc"
# List all files
ls -la
# Check stored scores
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='clojure' AND json_extract(er.run_config_json,'\$.model')='sonnet' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
