# Evaluation: language=clojure_model=opus_tooling=none · rep 2

## Summary

- **Factors:** language=clojure, model=opus, tooling=none
- **Status:** failed (archive incomplete — no source code files present)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** unavailable — no source files to build
- **Lint:** unavailable — no source files to lint
- **Architecture:** summary skill unavailable (no source to analyze)
- **Findings:** 13 items in `findings.jsonl` (1 critical, 12 high)

**Note:** retort.db reports test_coverage=1.0, code_quality=0.83, defect_rate=1.0 for this run, but the archive contains zero Clojure source or test files. Only `deps.edn` and `README.md` are present. The scores may have been computed against a workspace state that was not fully archived, or the archive was corrupted/truncated after scoring.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book | ✗ missing | No .clj files in workspace; src/ absent |
| R2 | GET /books lists all books | ✗ missing | No .clj files in workspace; src/ absent |
| R3 | GET /books ?author= filter | ✗ missing | No .clj files in workspace; src/ absent |
| R4 | GET /books/{id} returns single book | ✗ missing | No .clj files in workspace; src/ absent |
| R5 | PUT /books/{id} updates a book | ✗ missing | No .clj files in workspace; src/ absent |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No .clj files in workspace; src/ absent |
| R7 | Data stored in SQLite | ✗ missing | deps.edn declares sqlite-jdbc but no source implements it |
| R8 | JSON responses with HTTP status codes | ✗ missing | No .clj files in workspace; src/ absent |
| R9 | Input validation: title and author required | ✗ missing | No .clj files in workspace; src/ absent |
| R10 | GET /health endpoint | ✗ missing | No .clj files in workspace; src/ absent |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents setup, run, and test commands |
| R12 | At least 3 unit/integration tests | ✗ missing | No test/ directory; 0 test files found |

## Build & Test

```text
Build: not run — no source files present in archive
Stored scores from retort.db: test_coverage=1.0, code_quality=0.83, defect_rate=1.0
These scores contradict the archive state (0 source files).
```

```text
Tests: not run — no test files present in archive
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Lines of config (deps.edn + README.md) | 47 |
| Files (project, excl. meta) | 2 |
| Dependencies (deps.edn) | 7 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Archive incomplete — no Clojure source files in workspace
2. [high] POST /books endpoint missing — no source code
3. [high] GET /books list endpoint missing — no source code
4. [high] GET /books ?author= filter missing — no source code
5. [high] GET /books/{id} endpoint missing — no source code

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=opus_tooling=none/rep2
find . -name "*.clj" | wc -l          # 0 — no source files
cat deps.edn                            # config present but no implementation
cat README.md                           # README present
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='clojure' AND json_extract(er.run_config_json,'$.model')='opus' AND json_extract(er.run_config_json,'$.tooling')='none' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
