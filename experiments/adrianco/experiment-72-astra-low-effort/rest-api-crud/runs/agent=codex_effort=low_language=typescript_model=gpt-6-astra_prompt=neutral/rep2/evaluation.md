# Evaluation: agent=codex effort=low language=typescript model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (`test_coverage=1.0` ⇒ `npm run build` + `node --test` succeeded)
- **Lint:** n/a — `code_quality=0.733` from scores.json
- **Architecture:** single-module HTTP handler (`api.ts`) + thin `server.ts` entrypoint; no framework, no runtime deps
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `api.ts:59-64` INSERT + 201 + Location header |
| R2 | GET /books lists all | ✓ implemented | `api.ts:54-55` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `api.ts:56` bound param; `api.test.ts:61` |
| R4 | GET /books/{id} single | ✓ implemented | `api.ts:77`; 404 at `api.ts:76` |
| R5 | PUT /books/{id} update | ✓ implemented | `api.ts:78-82` UPDATE + 200 |
| R6 | DELETE /books/{id} | ✓ implemented | `api.ts:84-85` DELETE + 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `api.ts:2,36` node:sqlite DatabaseSync; persistence test `api.test.ts:88` |
| R8 | JSON + HTTP status codes | ✓ implemented | `api.ts:30-33` json(); 201/200/204/400/404/405/413/415 |
| R9 | Validate title+author required | ✓ implemented | `api.ts:8-17` validate(); `api.test.ts:67-77` |
| R10 | GET /health | ✓ implemented | `api.ts:47-50` returns {status:'ok'} after a DB probe |
| R11 | README with setup/run | ✓ implemented | `README.md` — install/build/start/test + endpoint table |
| R12 | ≥3 tests | ✓ implemented | `api.test.ts` — 6 tests, `test_coverage=1.0` |

## Build & Test

```text
npm test   (npm run build && node --test dist/api.test.js)
test_coverage=1.0 (scores.json) — build + all tests passed; not re-run per skill step 2
```

No skipped/disabled tests: `grep .skip|xit|xdescribe|it.todo` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .ts) | 218 |
| Files (source + config + docs) | 10 |
| Dependencies (dev only) | 2 (@types/node, typescript) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`) — all info-level, no deductions:

1. [info] Hardened request handling beyond spec (415 media-type, 413 1 MiB cap)
2. [info] Parameterized SQL guards author filter against injection
3. [info] Persistence verified across DB reopen
4. [info] Author filter is exact/case-sensitive (spec unspecified) — acceptable

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json                 # test_coverage=1.0 ⇒ build+tests passed
grep -rEc "\.skip\(|xit\(|xdescribe\(|it\.todo\(" *.ts   # 0 skips
grep -cE "^test\(" api.test.ts  # 6 tests
```
