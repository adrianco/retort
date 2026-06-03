# Evaluation: language=typescript_model=opus_tooling=beads · rep 2

## Summary

- **Factors:** language=typescript, model=opus, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=1.0 from retort.db (defect_rate=1.0)
- **Lint:** code_quality=0.733 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:13-34` — POST route accepts all four fields, inserts via prepared statement, returns 201 with created book |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:37-48` — GET /books returns all rows ordered by id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:39-43` — filters by author query param with parameterized SQL; tested in `tests/api.test.ts:49-66` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:50-59` — GET /books/:id with 404 handling; tested in `tests/api.test.ts:95-98` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:62-89` — PUT route with existence check, validation, and update; tested in `tests/api.test.ts:68-80` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:92-101` — DELETE route with 204 response and 404 on missing; tested in `tests/api.test.ts:82-93` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-24` — uses `better-sqlite3` with WAL mode, creates `books` table with AUTOINCREMENT |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes return JSON; status codes: 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:15-20` (POST) and `src/app.ts:73-78` (PUT) — validates both fields, returns 400; tested in `tests/api.test.ts:37-46` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/app.ts:9-11` — returns `{"status":"ok"}` with 200; tested in `tests/api.test.ts:18-21` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents install, build, run, dev, test commands, endpoint table, and curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/api.test.ts` — 8 test cases covering health, CRUD, validation, filtering, and 404 handling |

## Build & Test

```text
Source: retort.db stored scores (build/test not re-run per skill protocol)
test_coverage = 1.0 (build + all tests passed)
defect_rate   = 1.0 (build+test succeeded)
code_quality  = 0.733
```

```text
Test framework: vitest (via "npm test" → "vitest run")
8 test cases in tests/api.test.ts
0 skipped tests detected
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 239 (TS) |
| Files | 12 |
| Dependencies | 10 (3 runtime, 7 dev) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | N/A (score from DB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] All mechanical scores retrieved from retort.db — test_coverage=1.0, code_quality=0.733

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=opus_tooling=beads/rep2
cat stack.json
cat scores.json 2>/dev/null  # absent for this run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='typescript' AND json_extract(er.run_config_json,'$.model')='opus' AND json_extract(er.run_config_json,'$.tooling')='beads' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' . --include='*.ts' --include='*.js' | wc -l
find . -type f \( -name '*.ts' -o -name '*.js' \) -not -path '*/node_modules/*' -not -path '*/dist/*' -exec wc -l {} +
```
