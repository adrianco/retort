# Evaluation: effort=low_language=typescript_model=claude-fable-5-1_prompt=none · rep 2

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, effort=low, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0`
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` (retort.db, not re-run)
- **Lint:** pass — `code_quality=0.83` (retort.db) / 0.73 (scores.json)
- **Architecture:** inline below (run-summary not separately generated; 3-file app)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/app.ts:95-98` → `store.create`, `src/db.ts:29-34` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:91-93` → `store.list()`, `src/db.ts:36-42` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:92` reads `author`; `src/db.ts:40` `WHERE author = ?` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/app.ts:106-109`; 404 at :108 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:111-114`, `src/db.ts:50-55` (404 on no-change) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/app.ts:116-118`, `src/db.ts:57-59` → 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` `DatabaseSync`, table at :18-26 |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `send()` `src/app.ts:18-29`; 201/200/204/400/404/405/413 throughout |
| R9 | Validation: title & author required | ✓ implemented | `validateBook` `src/app.ts:53-58` → 400; test `tests/api.test.ts:52-60` |
| R10 | GET /health | ✓ implemented | `src/app.ts:85-88` → `{status:"ok"}` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — Setup/Run/Test/Endpoints sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 8 `test(...)` in `tests/api.test.ts`; `test_coverage=1.0` |

No requirements missing or partial. Enhancements beyond spec: `Location` header on create, 1 MB body guard (413), malformed-JSON → 400, `405` on wrong method.

## Build & Test

Scores read from `retort.db` / `scores.json` — toolchain **not re-run** per skill guidance.

```text
test_coverage = 1.0   # build succeeded + all tests passed (test gate)
defect_rate   = 1.0   # build+test succeeded
code_quality  = 0.83 (retort.db) / 0.73 (scores.json)
```

```text
node --test tests/*.test.ts   # 8 tests, 0 skipped (grep: 0 .skip/xit/it.todo)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 315 (src 210 + tests 105) |
| Files (source, excl. build/agent logs) | ~7 (src/*.ts ×3, tests ×1, README, package.json, tsconfig ×2) |
| Dependencies | 2 (both dev: `@types/node`, `typescript`; zero runtime deps) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; none affect scoring:

1. [info] E1 — Sets `Location` header on POST /books create (`src/app.ts:97`)
2. [info] E2 — Body-size guard (413) + malformed-JSON (400) (`src/app.ts:36,41-42`)
3. [info] N1 — PUT is a full replace requiring title+author, not a partial patch (`src/app.ts:112`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-1_prompt=none/rep2"
cat scores.json                 # stored mechanical scores (test_coverage/defect_rate/...)
grep -rEn "\.skip\(|xit\(|it\.todo\(" . --include="*.ts" | grep -v node_modules   # skip audit → 0
grep -cE "^test\(" tests/api.test.ts                                              # test count → 8
sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'\$.model')='claude-fable-5-1' AND json_extract(run_config_json,'\$.effort')='low' AND replicate=2 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
```
