# Evaluation: agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral · rep 4

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass — `test_coverage=1.0` (build + all tests passed; not re-run)
- **Lint:** pass — `code_quality=0.733` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/server.ts:31-37`, `src/books.ts:38-42` INSERT with all four fields |
| R2 | GET /books lists all books | ✓ implemented | `src/server.ts:30`, `src/books.ts:27-32` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:30` reads `author` param; `src/books.ts:28-29` `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/server.ts:42-45`; test asserts 404 at `test/api.test.ts:45` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/server.ts:46-52`, `src/books.ts:44-48` UPDATE + 404 on no change |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/server.ts:54`, `src/books.ts:50-51` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/books.ts:1,17` `node:sqlite` `DatabaseSync`, CREATE TABLE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `src/server.ts:4-7` `send()` sets JSON content-type; 201/200/404/400 used |
| R9 | Input validation: title & author required | ✓ implemented | `src/server.ts:16-23` `validInput`; test asserts 400 at `test/api.test.ts:40` |
| R10 | GET /health health check | ✓ implemented | `src/server.ts:29` returns `{status:'ok'}` |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md` — Setup/run, endpoints, tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test/api.test.ts` — 3 `test()` blocks; `test_coverage=1.0` |

## Build & Test

Build/test/lint were **not re-run** — scores were read from `scores.json` (inline gate output):

```text
scores.json:
  test_coverage = 1.0    (build + all tests passed)
  defect_rate   = 1.0    (build + test succeeded)
  code_quality  = 0.733  (lint/quality)
  maintainability = 0.858
  idiomatic     = 0.67
```

```text
test command: npm test  ->  tsx --test test/*.test.ts
3 tests, 0 failed, 0 skipped (not re-executed; test_coverage=1.0 confirms all passed)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 166 (src 120 + test 46) |
| Files | 3 |
| Dependencies | 3 (all devDependencies: @types/node, tsx, typescript; 0 runtime) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 4 findings are informational (no defects):

1. [info] Exactly 3 tests — meets the minimum, but each bundles several operations (`test/api.test.ts`)
2. [info] Zero runtime dependencies via Node 22 built-ins (`node:sqlite`, `node:http`)
3. [info] PUT /books/:id is a full replace requiring title+author — spec-consistent
4. [info] `?author=` filter is exact-match only — R3 satisfied

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep4"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rEc "\.skip\(|xit\(|xdescribe\(|it\.todo\(" test src --include="*.ts"   # skip count = 0
npm install && npm test                            # optional: re-execute the 3 tests
```
