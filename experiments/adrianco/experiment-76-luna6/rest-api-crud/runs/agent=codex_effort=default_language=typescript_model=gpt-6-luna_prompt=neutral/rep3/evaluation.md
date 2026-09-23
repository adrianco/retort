# Evaluation: agent=codex model=gpt-6-luna language=typescript prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass (test_coverage=1.0 ⇒ build + tests passed)
- **Lint:** pass — code_quality=0.6889 (scores.json), no separate lint re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.ts:103` route → `store.create` (`server.ts:70`) |
| R2 | GET /books lists all | ✓ implemented | `server.ts:98` → `store.list` (`server.ts:75`) |
| R3 | GET /books ?author= filter | ✓ implemented | `server.ts:99` reads param; `listByAuthor` (`server.ts:68`) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `server.ts:113-115`, 404 branch |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.ts:117-123` → `store.update` (`server.ts:79`) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.ts:125-126` → `store.delete` (`server.ts:84`) |
| R7 | SQLite / embedded DB | ✓ implemented | `node:sqlite` `DatabaseSync` (`server.ts:2,57`) |
| R8 | JSON + correct status codes | ✓ implemented | `sendJson` (`server.ts:18`); 201/200/404/400/204/413/500 |
| R9 | Validation: title & author required | ✓ implemented | `validateBook` (`server.ts:36-37`) |
| R10 | GET /health | ✓ implemented | `server.ts:97` returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented | `README.md:11-18` setup + run |
| R12 | ≥ 3 tests | ✓ implemented | 4 tests in `test/books.test.ts`; test_coverage=1.0 |

## Build & Test

```text
npm test   (npm run build && node --experimental-strip-types --test)
```

Not re-run — read from scores.json: `test_coverage=1.0` (build + all tests passed),
`defect_rate=1.0`. 4 tests, 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 142 (src/server.ts) |
| Test LOC | 41 (test/books.test.ts) |
| Files (src + test) | 2 |
| Dependencies | 0 runtime (node:http + node:sqlite built-ins) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| code_quality | 0.6889 |
| maintainability | 0.7949 |
| idiomatic | 0.78 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Tests exercise the store/validation layer, not the HTTP routes — no route/health test despite README claim (`test/books.test.ts:6`, `README.md:37`)
2. [info] DELETE 204 response sets a content-type header with an empty body (`server.ts:126`)
3. [info] `?author=` filter is exact-match only (`server.ts:68`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json          # test_coverage=1.0, defect_rate=1.0, code_quality=0.6889
grep -rEc "\.skip\(|xit\(|it\.todo\(" test src   # 0 skips
# npm test  # optional re-run: npm run build && node --experimental-strip-types --test
```
