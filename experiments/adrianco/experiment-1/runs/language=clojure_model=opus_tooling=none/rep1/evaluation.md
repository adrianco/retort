# Evaluation: language=clojure_model=opus_tooling=none · rep 1

## Summary

- **Factors:** language=clojure, model=opus, tooling=none
- **Status:** cannot-verify (source files missing from archive)
- **Requirements:** 3/12 implemented, 0 partial, 0 missing, 9 cannot-verify
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from test-output.txt
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** code_quality=0.833 from retort.db
- **Architecture:** summary skill not invoked (no source to analyze)
- **Findings:** 10 items in `findings.jsonl` (0 critical, 1 high, 9 medium)

**Note:** The `.clj` source files (src/ and test/ directories) were not included in the run archive. Only deps.edn, README.md, test-output.txt, and metadata files are present. The DB scores (test_coverage=1.0, defect_rate=1.0) and test output (8 tests, 18 assertions, 0 failures) confirm the code was generated and worked correctly, but direct source inspection is not possible.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a book | ? cannot-verify | `README.md:37` documents it; no `.clj` source archived |
| R2 | GET /books lists all books | ? cannot-verify | `README.md:38` documents it; no `.clj` source archived |
| R3 | GET /books ?author= filter | ? cannot-verify | `README.md:38` mentions filter; no `.clj` source archived |
| R4 | GET /books/{id} returns one book | ? cannot-verify | `README.md:39` documents it; no `.clj` source archived |
| R5 | PUT /books/{id} updates a book | ? cannot-verify | `README.md:40` documents it; no `.clj` source archived |
| R6 | DELETE /books/{id} deletes a book | ? cannot-verify | `README.md:41` documents it; no `.clj` source archived |
| R7 | Data stored in SQLite | ✓ implemented | `deps.edn:8` org.xerial/sqlite-jdbc, `deps.edn:7` next.jdbc; `README.md:24` "books.db" |
| R8 | JSON responses + HTTP status codes | ? cannot-verify | `deps.edn:4-6` ring-json + cheshire; `README.md:42` lists codes; no `.clj` source |
| R9 | Input validation (title/author) | ? cannot-verify | `README.md:42` "omissions return HTTP 400"; no `.clj` source |
| R10 | GET /health endpoint | ? cannot-verify | `README.md:36` lists /health; no `.clj` source archived |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` present with Stack, Setup, Run, Test, Endpoints sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test-output.txt:14` "Ran 8 tests containing 18 assertions. 0 failures, 0 errors." |

## Build & Test

```text
Build/test not re-run — using stored scores from retort.db:
  test_coverage  = 1.0  (build + all tests passed)
  code_quality   = 0.833
  defect_rate    = 1.0  (no defects detected)
  maintainability = 0.948
  idiomatic      = 0.85
  token_efficiency = 0.5
```

```text
Test output (from test-output.txt):
  Testing books.handler-test
  Ran 8 tests containing 18 assertions.
  0 failures, 0 errors.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | unknown (source files not archived; 66 lines in deps.edn + README.md) |
| Files | 6 (archived, excluding eval outputs) |
| Dependencies | 10 (8 main + 2 test, from deps.edn) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] Clojure source files (.clj) missing from run archive
2. [medium] POST /books: cannot verify — source not archived
3. [medium] GET /books: cannot verify — source not archived
4. [medium] GET /books ?author= filter: cannot verify — source not archived
5. [medium] GET /books/{id}: cannot verify — source not archived

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=opus_tooling=none/rep1

# Verify workspace
test -d . && test -f TASK.md && test -f stack.json

# Check for source files
find . -name "*.clj" -o -name "*.cljc"

# Read stored scores
sqlite3 -readonly ../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id = (SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='clojure'
      AND json_extract(er.run_config_json,'\$.model')='opus'
      AND json_extract(er.run_config_json,'\$.tooling')='none'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"

# Review test output
cat test-output.txt
```
