# Evaluation: language=clojure_model=sonnet_tooling=beads · rep 1

## Summary

- **Factors:** language=clojure, model=sonnet, tooling=beads
- **Status:** failed (no source code in archive — zero .clj files)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — no test files in archive
- **Build:** fail — no source code to build (test_coverage=0.0 from retort.db)
- **Lint:** unavailable — no source files to lint (code_quality=0.0 from retort.db)
- **Architecture:** summary skill unavailable (no source to analyze)
- **Findings:** 13 items in `findings.jsonl` (1 critical, 11 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book | ✗ missing | No .clj files in archive |
| R2 | GET /books lists all books | ✗ missing | No .clj files in archive |
| R3 | GET /books supports ?author= filter | ✗ missing | No .clj files in archive |
| R4 | GET /books/{id} returns single book | ✗ missing | No .clj files in archive |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .clj files in archive |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .clj files in archive |
| R7 | Data stored in SQLite | ✗ missing | deps.edn references sqlite-jdbc but no code uses it |
| R8 | JSON responses with HTTP status codes | ✗ missing | No route handlers exist |
| R9 | Input validation: title and author required | ✗ missing | No validation logic exists |
| R10 | GET /health health-check endpoint | ✗ missing | No route handlers exist |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents setup, run, test commands, and all API endpoints |
| R12 | At least 3 unit/integration tests | ✗ missing | No test/ directory; test-output.txt shows 6 tests ran previously but source files absent |

## Build & Test

```text
No build attempted — no source code exists in the archive.
All retort.db scores are 0.0:
  test_coverage=0.0  code_quality=0.0  defect_rate=0.0
  maintainability=0.0  idiomatic=0.0  token_efficiency=0.0
```

```text
test-output.txt (captured from original run, not reproducible from archive):
  6 tests, 25 assertions, 0 failures.
Note: test source files are not present in the archive.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (no .clj files) |
| Lines of config (deps.edn + tests.edn) | 20 |
| Files | 10 |
| Dependencies (in deps.edn) | 8 |
| Tests total | 0 (in archive) |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No source code in archive — zero .clj files; no src/ or test/ directories
2. [high] R1: POST /books not implemented — no source code
3. [high] R2: GET /books not implemented — no source code
4. [high] R3: GET /books ?author= filter not implemented — no source code
5. [high] R4: GET /books/{id} not implemented — no source code

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=beads/rep1
find . -name "*.clj"                    # confirms zero source files
cat stack.json                           # {"language":"clojure","agent":"unknown","framework":"unknown"}
cat test-output.txt                      # shows 6 tests from original run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='clojure' AND json_extract(er.run_config_json,'\$.model')='sonnet' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1) AND rr.metric_name IN ('test_coverage','code_quality','defect_rate');"
```
