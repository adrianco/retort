# Evaluation: language=typescript_model=claude-opus-4-7_tooling=none · rep 3

## Summary

- **Factors:** language=typescript, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — defect_rate=1.0 from retort.db
- **Lint:** code_quality=0.7333 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:57-70` — POST route inserts all four fields via prepared statement |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:72-85` — returns all rows ordered by id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:73-78` — checks `req.query.author` and filters with WHERE clause |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:87-99` — parameterized route with 404 handling |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:101-126` — validates input, checks existence, updates all fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:128-138` — deletes by id, returns 204, 404 if not found |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-24` — better-sqlite3 with WAL mode; `src/server.ts:6` defaults to `books.db` file |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes return JSON; codes: 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:12-47` — `validateBookInput` rejects empty/missing title or author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:53-55` — returns `{"status":"ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents npm install, dev/prod run, test, env vars, and all endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 15 test cases covering all endpoints including validation edge cases |

## Build & Test

```text
# Build (from retort.db scores — not re-run)
defect_rate=1.0 → build + all tests succeeded
test_coverage=0.9102 → tests ran with ~91% coverage
```

```text
# Test framework: Jest with ts-jest (jest --runInBand)
# 15 test cases in tests/books.test.ts
# Covers: health check, CRUD operations, validation (missing title/author, invalid year),
#         author filtering, 404 handling on get/update/delete
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 352 (TS/JS) |
| Files | 13 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| test_coverage (retort.db) | 0.9102 |
| code_quality (retort.db) | 0.7333 |
| idiomatic (retort.db) | 0.68 |
| maintainability (retort.db) | 0.6851 |
| token_efficiency (retort.db) | 1.0 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] Code quality score below threshold (0.73) — lint/style issues likely present
2. [low] Test coverage at 91% — minor edge-case gaps remain

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep3
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT metric_name, value FROM run_results WHERE run_id = (SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'$.language')='typescript' AND json_extract(run_config_json,'$.model')='claude-opus-4-7' AND json_extract(run_config_json,'$.tooling')='none' AND replicate=3 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
cat REQUIREMENTS.json 2>/dev/null || cat ../../REQUIREMENTS.json
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' tests/ --include="*.ts" 2>/dev/null | wc -l
find . -type f -not -path "*/node_modules/*" -not -path "*/dist/*" | wc -l
```
