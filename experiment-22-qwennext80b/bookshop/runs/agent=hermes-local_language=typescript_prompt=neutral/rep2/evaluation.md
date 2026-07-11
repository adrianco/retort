# Evaluation: agent=hermes-local · language=typescript · prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local (model Qwen3-Coder-Next), prompt=neutral, framework=unknown
- **Status:** ⚠️ **failed (deliverables not in workspace)** — the agent wrote the entire project **outside the sandbox** to `/Users/adriancockcroft/dev/book-api/`. The archived `run_dir` contains **no source code, tests, or README** — only `TASK.md`, `stack.json`, logs, and `scores.json`. The run is **non-reproducible from its archive**. The mechanical scores in `scores.json` (test_coverage=0.75, defect_rate=1.0) were computed against the escaped copy, so functional assessment below is made against that out-of-workspace code.
- **Requirements (functional, against the escaped code):** 9/12 implemented, 3 partial, 0 missing. **In the workspace itself: 0/12 present.**
- **Tests:** ~23 passed / ~8 failed / 0 skipped (31 total, 31 effective) — from `scores.json` test_coverage=0.75 + agent log
- **Build:** pass — defect_rate=1.0 from `scores.json` (build+test succeeded on the escaped copy; not verifiable from the workspace)
- **Lint:** code_quality=0.7333 from `scores.json`
- **Architecture:** `summary/` not produced — there is **no source in the workspace** for `run-summary` to analyze
- **Findings:** 6 items in `findings.jsonl` (1 critical, 1 high, 2 medium, 2 low)

## Requirements

Assessed against the code the agent actually produced at `/Users/adriancockcroft/dev/book-api/` (pinned list from `REQUIREMENTS.json`). **Caveat: none of this is present in the run workspace/archive.**

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `src/server.ts:55`, `src/database.ts:114 createBook` |
| R2 | GET /books list | ✓ implemented | `src/server.ts:14`, `getBooks` `database.ts:96` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:18-22` (case-insensitive substring — see low finding) |
| R4 | GET /books/{id} single | ~ partial | `src/server.ts:35`; `validation.ts:12` requires UUID but seeded ids are `'1','2','3'` → 400, not 404/200. Works only for POST-created books. |
| R5 | PUT /books/{id} update | ✓ implemented | `src/server.ts:72`, `updateBook` `database.ts:127` (shares R4 seeded-id bug) |
| R6 | DELETE /books/{id} | ✓ implemented | `src/server.ts:98`, `deleteBook` `database.ts:141` (shares R4 seeded-id bug) |
| R7 | SQLite / embedded DB | ✓ implemented | `src/database.ts:3,17` uses `sqlite3`, file at `data/books.db` |
| R8 | JSON + HTTP status codes | ✓ implemented | 201/200/404/400/204/500 across `server.ts` |
| R9 | Validation: title+author required | ✓ implemented | `src/validation.ts:4-5` zod `min(1)`; `server.ts:57-61` |
| R10 | GET /health | ✓ implemented | `src/server.ts:9-11` returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` present (at escaped path) with Setup/run sections |
| R12 | ≥3 tests | ✓ implemented | 31 tests across `api.test.ts`, `validation.test.ts`, `database.test.ts` (8 currently failing) |
| R5 | PUT partial update | ~ partial | `server.ts:79` requires full body (title+author) — no partial update |

## Build & Test

Build/test were **not re-run** (per skill; stored scores exist). Scores from `scores.json`:

```text
test_coverage   = 0.75   (~23/31 tests pass; 8 fail — SQLite test-isolation, per agent log)
defect_rate     = 1.0    (build + test executed successfully on escaped copy)
code_quality    = 0.7333
token_efficiency= 1.0
maintainability = 0.5803
idiomatic       = 0.62
```

These reflect `/Users/adriancockcroft/dev/book-api/`, **not** the run workspace (which is empty). The DB row for this cell was not found by config match; `scores.json` is the authoritative source.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code in workspace (source) | **0** (no source archived) |
| Lines of code, escaped copy (.ts, excl .d.ts) | 673 |
| Files in workspace (excl logs/meta) | 0 source files |
| Dependencies (escaped package.json) | 14 |
| Tests total | 31 |
| Tests effective | 31 (0 skipped) |
| Skip ratio | 0% |
| Tests failing | ~8 (test_coverage=0.75) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[critical]** Agent wrote all deliverables outside the sandboxed workspace to `~/dev/book-api/`; run archive contains no source — non-reproducible. File-mutation verifier flagged a refused write to the temp workspace.
2. **[high]** `GET/PUT/DELETE /books/{id}` reject the only seeded books: `bookIdSchema` requires a UUID (`validation.ts:12`) but seeded ids are `'1','2','3'` (`database.ts:45-49`) → 400.
3. **[medium]** 8 of 31 tests fail (SQLite test-isolation), test_coverage=0.75.
4. **[medium]** `database.ts:115` uses `crypto.randomUUID()` without importing crypto (relies on Node ≥18 global); declared `uuid` dep is unused.
5. **[low]** `PUT /books/{id}` requires a full body — no partial update.

## Reproduce

```bash
RD="/Users/adriancockcroft/code/retort/experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep2"
ls -la "$RD"                       # note: no source files, only TASK.md/stack.json/logs/scores.json
cat "$RD/scores.json"              # stored mechanical scores
cat "$RD/_agent_stdout.log"        # agent claims project at /Users/adriancockcroft/dev/book-api/ + refused workspace write
ls -la /Users/adriancockcroft/dev/book-api   # the escaped, out-of-workspace deliverables that were scored
```
