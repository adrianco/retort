# Evaluation: language=clojure_model=opus_tooling=beads · rep 2

## Summary

- **Factors:** language=clojure, model=opus, tooling=beads
- **Status:** cannot-verify (source files missing from archive)
- **Requirements:** 1/12 implemented, 11 cannot-verify (indirect evidence from DB scores + README)
- **Tests:** unavailable (test files absent from archive; test_coverage=1.0 from retort.db)
- **Build:** unavailable (no source to build; test_coverage=1.0 and defect_rate=1.0 from retort.db suggest build succeeded at scoring time)
- **Lint:** unavailable (no source files in archive; code_quality=0.8333 from retort.db)
- **Architecture:** summary skill unavailable (no source to analyze)
- **Findings:** 12 items in `findings.jsonl` (1 critical, 9 high, 2 medium)

## Archive Integrity

**CRITICAL: The archive is incomplete.** The `src/` and `test/` directories referenced by `deps.edn` are absent. Only configuration and documentation files are present (deps.edn, README.md, TASK.md, stack.json, _meta.json, CLAUDE.md, AGENTS.md, .gitignore). The retort.db scores (test_coverage=1.0, defect_rate=1.0) and `_meta.json` (`"succeeded": true`) indicate the implementation existed and passed all tests at scoring time. The source was likely lost during archival.

## Stored Scores (retort.db)

| Metric | Value |
|--------|-------|
| test_coverage | 1.0 |
| code_quality | 0.8333 |
| defect_rate | 1.0 |
| maintainability | 0.9433 |
| idiomatic | 0.87 |
| token_efficiency | 0.5 |

## Requirements

Uses pinned requirement list from `experiment-1/REQUIREMENTS.json` (12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ? cannot-verify | No src/ in archive; README.md documents endpoint; test_coverage=1.0 |
| R2 | GET /books lists all books | ? cannot-verify | No src/ in archive; README.md documents endpoint; test_coverage=1.0 |
| R3 | GET /books ?author= filter | ? cannot-verify | No src/ in archive; README.md documents filter; test_coverage=1.0 |
| R4 | GET /books/{id} returns single book | ? cannot-verify | No src/ in archive; README.md documents endpoint; test_coverage=1.0 |
| R5 | PUT /books/{id} updates a book | ? cannot-verify | No src/ in archive; README.md documents endpoint; test_coverage=1.0 |
| R6 | DELETE /books/{id} deletes a book | ? cannot-verify | No src/ in archive; README.md documents endpoint; test_coverage=1.0 |
| R7 | Data stored in SQLite / embedded DB | ? cannot-verify | `deps.edn`: sqlite-jdbc 3.46.0.0 + next.jdbc 1.3.939 declared; no source to verify usage |
| R8 | JSON responses with HTTP status codes | ? cannot-verify | `deps.edn`: ring-json 0.5.1 + cheshire 5.13.0 declared; no handler source |
| R9 | Input validation (title, author required) | ? cannot-verify | No handler source; README.md notes required fields; test_coverage=1.0 |
| R10 | GET /health endpoint | ? cannot-verify | No handler source; README.md documents /health; test_coverage=1.0 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md`: setup (clojure -P), run (clojure -M:run), test (clojure -X:test), endpoints table, examples |
| R12 | At least 3 unit/integration tests | ? cannot-verify | No test/ directory; test_coverage=1.0 suggests tests existed at scoring time |

## Build & Test

```text
Build/test commands cannot be run — source files absent from archive.
deps.edn declares: clojure -M:run (server), clojure -X:test (tests)
retort.db scores: test_coverage=1.0, defect_rate=1.0 (build+tests passed at scoring time)
```

## Skipped Tests

Cannot analyze — no test files in archive.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (source files absent) |
| Files (in archive) | 8 (excluding evaluation outputs) |
| Dependencies (from deps.edn) | 8 main + 2 test |
| Tests total | unavailable |
| Tests effective | unavailable |
| Skip ratio | unavailable |
| Build duration | unavailable |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Source and test files missing from archive — no src/ or test/ directories
2. [high] R1: POST /books — cannot verify, source absent
3. [high] R2: GET /books — cannot verify, source absent
4. [high] R3: GET /books ?author= filter — cannot verify, source absent
5. [high] R4: GET /books/{id} — cannot verify, source absent

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=opus_tooling=beads/rep2

# Verify archive contents
find . -type f -not -path "*/.git/*" | sort

# Check stored scores
sqlite3 -readonly ../../retort.db "
  SELECT rr.metric_name, rr.value
  FROM run_results rr
  WHERE rr.run_id = (
      SELECT er.id FROM experiment_runs er
      WHERE json_extract(er.run_config_json,'$.language')='clojure'
        AND json_extract(er.run_config_json,'$.model')='opus'
        AND json_extract(er.run_config_json,'$.tooling')='beads'
        AND er.replicate=2 AND er.status='completed'
      ORDER BY er.finished_at DESC LIMIT 1);"

# NOTE: Cannot run build/test — source files missing
```
