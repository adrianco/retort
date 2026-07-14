# Evaluation: language=typescript_model=sonnet_tooling=beads · rep 3

## Summary

- **Factors:** language=typescript, model=sonnet, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — test_coverage=0.9402, defect_rate=1.0 from retort.db
- **Lint:** pass — code_quality=0.733 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `src/app.ts:25-41` — POST route accepts title, author, year, isbn; test at `src/__tests__/books.test.ts:20-31` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:44-52` — GET route returns full collection; test at `src/__tests__/books.test.ts:60-75` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:46-48` — LIKE query on author param; test at `src/__tests__/books.test.ts:77-85` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `src/app.ts:56-62` — returns book or 404; test at `src/__tests__/books.test.ts:88-105` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:65-91` — partial update with validation; test at `src/__tests__/books.test.ts:107-131` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:94-101` — returns 204; test at `src/__tests__/books.test.ts:133-149` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-23` — uses better-sqlite3 with WAL mode |
| R8 | JSON responses with proper HTTP codes | ✓ implemented | 201 (create), 200 (get/list/update), 204 (delete), 404 (not found), 400 (validation) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:28-33` (POST), `src/app.ts:72-78` (PUT); tests at `src/__tests__/books.test.ts:33-57` |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:20-22` — returns `{status: "ok"}`; test at `src/__tests__/books.test.ts:11-16` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — documents setup, running, API endpoints, and testing |
| R12 | At least 3 unit/integration tests | ✓ implemented | 15 tests in `src/__tests__/books.test.ts` covering all endpoints |

## Build & Test

```text
Scores from retort.db (build/test not re-run):
  test_coverage  = 0.9402
  code_quality   = 0.7333
  defect_rate    = 1.0 (build + test succeeded)
  maintainability = 0.6533
  idiomatic      = 0.7200
  token_efficiency = 0.5000
```

```text
Test framework: Jest (ts-jest preset)
Test file: src/__tests__/books.test.ts
Test count: 15 test cases across 6 describe blocks
Skipped: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 305 |
| Files | 12 |
| Dependencies | 12 (2 prod + 10 dev) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Findings

Top 3 by severity (full list in `findings.jsonl`):

1. [medium] Code quality score below threshold (0.73) — lint warnings in generated code
2. [low] Maintainability score moderate (0.65) — all routes in single app.ts file
3. [info] Dead conditional app export in app.ts:118-123 — unused require.main check

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=sonnet_tooling=beads/rep3

# Read stored scores (do not re-run build/test)
sqlite3 -readonly ../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id = (SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='typescript'
      AND json_extract(er.run_config_json,'\$.model')='sonnet'
      AND json_extract(er.run_config_json,'\$.tooling')='beads'
      AND er.replicate=3 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"

# Count skipped tests
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts" --include="*.js" | wc -l

# Count test cases
grep -cE "^\s*(it|test)\s*\(" src/__tests__/books.test.ts

# Lines of code
find . -type f \( -name "*.ts" -o -name "*.js" \) -not -path "*/node_modules/*" -exec wc -l {} +

# File count
find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" | wc -l
```
