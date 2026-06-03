# Evaluation: language=go_model=sonnet_tooling=none · rep 3

## Summary

- **Factors:** language=go, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=0.661, defect_rate=1.0 from retort.db
- **Lint:** pass — code_quality=0.956 from retort.db
- **Architecture:** single-file Go service with manual routing, clean App struct pattern
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Stored Scores (retort.db)

| Metric | Value |
|--------|-------|
| test_coverage | 0.661 |
| code_quality | 0.956 |
| defect_rate | 1.0 |
| maintainability | 0.990 |
| idiomatic | 0.720 |
| token_efficiency | 0.500 |

## Requirements

Source: `experiment-1/REQUIREMENTS.json` (pinned list, 12 requirements)

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `main.go:141-165` createBook handler accepts all four fields, inserts via SQL |
| R2 | GET /books lists all books | ✓ implemented | `main.go:111-139` listBooks queries all rows |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:112` reads `r.URL.Query().Get("author")`, filters via SQL WHERE clause |
| R4 | GET /books/{id} returns single book | ✓ implemented | `main.go:167-180` getBook with 404 on ErrNoRows |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:182-213` updateBook checks existence, validates, updates |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:215-227` deleteBook returns 204 No Content |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:13` imports `modernc.org/sqlite`, `main.go:29` opens sqlite DB |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `main.go:59-67` writeJSON/writeError helpers; 201 create, 200 get/list/update, 204 delete, 400 validation, 404 not found |
| R9 | Input validation: title and author required | ✓ implemented | `main.go:147-153` createBook + `main.go:196-203` updateBook check TrimSpace != "" |
| R10 | GET /health health-check endpoint | ✓ implemented | `main.go:107-109` returns `{"status":"ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | README.md has setup, build, test, endpoint docs, and curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 tests: TestHealth, TestCreateAndGetBook, TestCreateBookValidation, TestListAndFilterBooks, TestUpdateBook, TestDeleteBook, TestNotFound |

## Build & Test

Build and test results from retort.db stored scores (not re-run):
- **test_coverage=0.661**: tests executed successfully (defect_rate=1.0 confirms build+test pass)
- **code_quality=0.956**: near-perfect lint score

```text
Tests (from main_test.go):
  TestHealth              — verifies GET /health returns 200
  TestCreateAndGetBook    — POST + GET round-trip, checks 201 and field values
  TestCreateBookValidation — missing title → 400, missing author → 400
  TestListAndFilterBooks  — creates 3 books, lists all (3), filters by author (2)
  TestUpdateBook          — POST then PUT, verifies updated title
  TestDeleteBook          — POST then DELETE (204), confirms GET returns 404
  TestNotFound            — GET /books/9999 returns 404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 430 (main.go: 245, main_test.go: 185) |
| Files (source + config) | 4 (main.go, main_test.go, README.md, go.mod) |
| Dependencies (go.mod indirect) | 10 |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Unchecked error from json.Encode in writeJSON — `main.go:62`
2. [low] Ignored error from LastInsertId — `main.go:162`
3. [info] No go.sum lock file in archive

## Reproduce

```bash
cd experiment-1/runs/language=go_model=sonnet_tooling=none/rep3
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT metric_name, value FROM run_results WHERE run_id = (SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'$.language')='go' AND json_extract(run_config_json,'$.model')='sonnet' AND json_extract(run_config_json,'$.tooling')='none' AND replicate=3 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go"
```
