# Evaluation: typescript · gpt-oss-20b · rep 2

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.6889` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/index.ts:32` inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/index.ts:58` `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:52-53` filters by author query param |
| R4 | GET /books/{id} single book | ✓ implemented | `src/index.ts:66` returns row or 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/index.ts:76` UPDATE, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/index.ts:96` DELETE, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/index.ts:9` `sqlite3.Database(':memory:')` + SQL schema (in-memory, not durable — see findings) |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/400/404/204/500 across handlers, all `res.json(...)` |
| R9 | Validation: title & author required | ✓ implemented | `src/index.ts:24-29` `validateBook`, 400 on missing |
| R10 | GET /health | ✓ implemented | `src/index.ts:109` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` install/run/test sections (minor `pm run dev` typo) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `__tests__/api.test.ts` — 7 tests, `test_coverage=0.9558`, all pass |

## Build & Test

Build/test not re-run — stored scores used (per skill guidance).

```text
scores.json: test_coverage=0.9558, defect_rate=1.0  (build + jest tests all pass)
code_quality=0.6889, maintainability=0.5465, idiomatic=0.38
```

```text
jest — 7 tests (health, create, list, filter-by-author, get-by-id, update, delete)
0 failed / 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 182 (118 src + 64 tests) |
| Files | 2 source (1 impl, 1 test) |
| Dependencies | 10 (2 runtime, 8 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] README dev command typo `pm run dev` — `README.md:21`
2. [low] `year || null` coerces year 0 / empty isbn to null — `src/index.ts:39,85`
3. [info] SQLite database is in-memory only, not durable — `src/index.ts:9`

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep2
cat scores.json                     # stored mechanical scores (no re-run)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts"   # 0 skips
npm install && npm test             # optional: re-run the 7 jest tests
```
