# Evaluation: agent=codex effort=low language=typescript model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — `tsc` succeeded (test_coverage=1.0 from scores.json; build runs as part of `npm test`)
- **Lint:** unavailable — no linter configured; code_quality=0.733 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Stored scores (`scores.json`): test_coverage=1.0, defect_rate=1.0, code_quality=0.733, maintainability=0.730, idiomatic=0.87, token_efficiency=0.0103. The prompt factor (`neutral`) prescribes no methodology and only asks for tests — no additional checkable requirements beyond R12.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.ts:69-77` INSERT + 201 + Location; test `app.test.ts:57` |
| R2 | GET /books lists all books | ✓ implemented | `app.ts:58-67` SELECT * ORDER BY id; test `app.test.ts:54,82` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.ts:59-66` WHERE author = ?; test `app.test.ts:75-84` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.ts:87-91`; 404 test `app.test.ts:106` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.ts:93-104` (full replace, 404 if missing); test `app.test.ts:65-69` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.ts:106-110`; test `app.test.ts:70-71` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `app.ts:2,37` `node:sqlite` DatabaseSync, on-disk file; reopen-persistence test `app.test.ts:116-127` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/400/413/415/500 across `app.ts:53-125`; JSON content-type asserted `app.test.ts:52` |
| R9 | Validation: title and author required | ✓ implemented | `app.ts:11-33` validate(); 400 test matrix `app.test.ts:87-101` |
| R10 | GET /health health check | ✓ implemented | `app.ts:53-56` (with `SELECT 1` DB probe); test `app.test.ts:50-53` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-25` npm ci/build/start + test, env vars, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 tests in `app.test.ts`; test_coverage=1.0 |

No partial or missing requirements. No requirement scored on a stub.

## Build & Test

Build and tests were **not** re-run — stored scores used per the skill (test_coverage=1.0 ⇒ build + all tests passed). The archived agent log confirms the final green run:

```text
npm test   (npm run build && node --test dist/app.test.js)
> tsc
✔ health and initially empty collection return JSON
✔ create, retrieve, replace and delete a book
✔ author filter matches exactly and treats SQL as data
✔ invalid bodies are rejected without changing stored data
✔ missing books, invalid IDs and unknown routes have JSON errors
✔ books persist when the database is reopened
ℹ tests 6  ℹ pass 6  ℹ fail 0  ℹ skipped 0  ℹ todo 0
exit_code 0
```

Note: the agent's first test attempt bound a network port and failed with `listen EPERM` under the sandbox; it then rewrote the tests to drive Express in-process via `IncomingMessage`/`ServerResponse` (no port). The final suite passes and still exercises real Express + SQLite behavior.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only: app.ts + server.ts + app.test.ts) | 277 |
| Files (source, excl. lockfile/build) | 6 |
| Dependencies (prod + dev) | 4 (express, @types/express, @types/node, typescript) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | not separately measured (build folded into test run) |

## Findings

All 3 findings are `info` (enhancements / context) — none affect the score:

1. [info] Parameterized SQL and DB-level CHECK constraints beyond spec (`app.ts:42-43,66,73`)
2. [info] Structured error handling (413/400/415/500) and graceful shutdown beyond spec (`app.ts:113-125`, `server.ts:16-23`)
3. [info] Tests adapted to in-process HTTP after sandbox blocked `listen()` — valid adaptation, 6/6 pass

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
run_dir="experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=typescript_model=gpt-6-astra_prompt=neutral/rep2"
cat "$run_dir/scores.json"          # stored mechanical scores (source of truth)
cat "$run_dir/../../../REQUIREMENTS.json"   # pinned R1..R12 checklist
# Do NOT re-run the toolchain; scores.json already records test_coverage=1.0.
```
