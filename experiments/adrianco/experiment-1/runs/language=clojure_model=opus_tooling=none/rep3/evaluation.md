# Evaluation: language=clojure_model=opus_tooling=none · rep 3

## Summary

- **Factors:** language=clojure, model=opus, tooling=none
- **Status:** cannot-verify (source code missing from archive — DB scores indicate a successful run)
- **Requirements:** 1/12 implemented, 11 partial (cannot-verify — archive incomplete), 0 missing
- **Tests:** test_coverage=1.0 from retort.db (tests passed at run time); 0 test files in archive
- **Build:** cannot-verify — test_coverage=1.0 and defect_rate=1.0 in retort.db indicate build+tests passed; no source to rebuild
- **Lint:** code_quality=0.833 from retort.db; no source to re-lint
- **Architecture:** no source code in archive; summary skill not applicable
- **Findings:** 12 items in `findings.jsonl` (1 critical, 11 high, 0 medium, 0 low, 0 info)

> **Note:** retort.db reports test_coverage=1.0, code_quality=0.833, defect_rate=1.0, maintainability=0.977, idiomatic=0.83 for this run. `_meta.json` confirms `succeeded: true`. The agent produced working code, but the archive contains only `deps.edn` and `README.md` — all `.clj` source and test files are absent. This pattern is consistent across all 3 reps of this cell, pointing to a systematic archival issue rather than an agent failure.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ? cannot-verify | README.md:18 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R2 | GET /books lists all books | ? cannot-verify | README.md:19 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R3 | GET /books supports ?author= filter | ? cannot-verify | README.md:19 documents filter; test_coverage=1.0; no .clj source in archive |
| R4 | GET /books/{id} returns single book | ? cannot-verify | README.md:20 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R5 | PUT /books/{id} updates a book | ? cannot-verify | README.md:21 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R6 | DELETE /books/{id} deletes a book | ? cannot-verify | README.md:22 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R7 | Data stored in SQLite | ? cannot-verify | deps.edn:7-8 declares sqlite-jdbc + next.jdbc; test_coverage=1.0; no source to verify usage |
| R8 | JSON responses with HTTP status codes | ? cannot-verify | deps.edn:6 declares cheshire; test_coverage=1.0; no source to verify |
| R9 | Input validation: title and author required | ? cannot-verify | README.md:40 states required; test_coverage=1.0; no source to verify logic |
| R10 | GET /health health-check endpoint | ? cannot-verify | README.md:17 documents endpoint; test_coverage=1.0; no .clj source in archive |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 50 lines covering setup, run, test commands, endpoints, and examples |
| R12 | At least 3 unit/integration tests | ? cannot-verify | test_coverage=1.0 from retort.db; deps.edn:11-14 configures test-runner + ring-mock; no test/ dir in archive |

## Build & Test

```text
Build/Test: NOT RE-RUN — using stored scores from retort.db

  test_coverage    = 1.0   (build + all tests passed at run time)
  defect_rate      = 1.0   (build+test succeeded)
  code_quality     = 0.833
  maintainability  = 0.977
  idiomatic        = 0.83
  token_efficiency = 0.5

Archive state: 0 .clj files present; src/ and test/ directories absent.
  find . -name '*.clj' | wc -l → 0
  Only deps.edn, README.md, stack.json, TASK.md, _meta.json in archive.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (.clj files — not archived) |
| Lines of config | 16 (deps.edn) |
| Lines of documentation | 50 (README.md) |
| Files (in archive) | 5 (deps.edn, README.md, stack.json, TASK.md, _meta.json) |
| Dependencies (declared) | 7 runtime (clojure, ring-core, ring-jetty-adapter, reitit, cheshire, next.jdbc, sqlite-jdbc) + 2 test (test-runner, ring-mock) |
| Tests total | unknown (test files not archived) |
| Tests effective | unknown (test_coverage=1.0 from DB) |
| Skip ratio | unknown |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Source code missing from archive — src/ and test/ directories not persisted
2. [high] R1: POST /books — cannot verify from archive, source missing
3. [high] R2: GET /books list — cannot verify from archive, source missing
4. [high] R3: GET /books ?author= filter — cannot verify from archive, source missing
5. [high] R4: GET /books/{id} — cannot verify from archive, source missing

Plus 7 additional high-severity cannot-verify findings (R5–R10, R12) — all due to missing source files.

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=opus_tooling=none/rep3
find . -name '*.clj' | wc -l          # expect 0 — no source archived
ls -la                                  # only deps.edn, README.md, metadata
cat _meta.json                         # succeeded: true
cat deps.edn                           # full project config with correct deps
# Compare with retort.db:
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='clojure' AND json_extract(er.run_config_json,'\$.model')='opus' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
