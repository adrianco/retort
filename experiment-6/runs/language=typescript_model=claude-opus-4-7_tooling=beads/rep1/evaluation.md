# Evaluation: language=typescript_model=claude-opus-4-7_tooling=beads · rep 1

## Summary

- **Factors:** language=typescript, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass (test_coverage=0.9175, defect_rate=1.0 from retort.db)
- **Lint:** pass with warnings — code_quality=0.733 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:13-20` POST route; `src/db.ts:39-49` create(); `tests/api.test.ts:28-67` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:22-26` GET route; `src/db.ts:52-59` list(); `tests/api.test.ts:70-90` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:23` extracts author query param; `src/db.ts:53-56` WHERE clause; `tests/api.test.ts:86-89` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:28-37` GET /:id route; `src/db.ts:61-64` get(); `tests/api.test.ts:93-111` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:40-54` PUT route; `src/db.ts:67-82` update(); `tests/api.test.ts:114-140` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:56-66` DELETE route; `src/db.ts:84-87` delete(); `tests/api.test.ts:143-158` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1` imports better-sqlite3; `src/db.ts:22-23` opens Database; `package.json` dependency |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/app.ts` uses 200/201/204/400/404 consistently; tests verify all status codes |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:19-24` validates non-empty strings; `tests/api.test.ts:42-58` tests missing/blank fields |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/app.ts:9-11` returns `{status:'ok'}`; `tests/api.test.ts:19-24` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup, Run, Test, Endpoints sections with examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 15 test cases in `tests/api.test.ts` using supertest + in-memory SQLite |

## Build & Test

```text
Stored scores from retort.db (build/test NOT re-run):
  test_coverage  = 0.9175
  defect_rate    = 1.0  (build+test succeeded)
  code_quality   = 0.733
  maintainability = 0.729
  idiomatic      = 0.9
  token_efficiency = 1.0
```

```text
Test command: npm test (jest --runInBand)
15 test cases across 6 describe blocks:
  GET /health          (1 test)
  POST /books          (4 tests)
  GET /books           (2 tests)
  GET /books/:id       (3 tests)
  PUT /books/:id       (3 tests)
  DELETE /books/:id    (2 tests)
0 skipped tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 256 (app:77 + db:92 + validation:65 + server:22) |
| Lines of code (incl. tests) | 443 |
| Files (project, excl. node_modules) | 17 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | 189s (full agent run) |
| Agent tokens | 1,220,231 |
| Agent cost | $1.06 |
| Agent turns | 36 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] code_quality score 0.733 indicates lint/style issues
2. [info] Comprehensive input validation beyond spec requirements
3. [info] Clean separation of concerns across modules
4. [info] Thorough test suite with 15 test cases covering all endpoints

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-7_tooling=beads/rep1
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT metric_name, value FROM run_results rr WHERE rr.run_id = (SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'\$.language')='typescript' AND json_extract(run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(run_config_json,'\$.tooling')='beads' AND replicate=1 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
cat REQUIREMENTS.json
grep -cE '^\s*it\(' tests/api.test.ts
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' tests/ --include="*.ts" 2>/dev/null | wc -l
wc -l src/app.ts src/db.ts src/validation.ts src/server.ts tests/api.test.ts
```
