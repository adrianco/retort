# Evaluation: rest-api-crud · agent=codex effort=low model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass (test gate ran `tsc` + `node --test`; `test_coverage=1.0`, `defect_rate=1.0`)
- **Lint:** n/a — `code_quality=0.733` from scores.json
- **Architecture:** single-module request router (`books.ts`) + thin Node http adapter (`server.ts`); `run-summary` skill unavailable in this session
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12). The neutral prompt adds no checkable requirements (P-list empty).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.ts:62-64` INSERT ... RETURNING, 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `books.ts:48` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `books.ts:47-49` WHERE author=?; tested `books.test.ts:41` |
| R4 | GET /books/{id} single book | ✓ implemented | `books.ts:74-75`, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `books.ts:66-67` UPDATE ... RETURNING, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `books.ts:70-72` returns 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `books.ts:1,24` node:sqlite DatabaseSync; reopen test `books.test.ts:67` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `Response.json` throughout; 201/200/204/400/404/405/413 |
| R9 | Validation: title & author required | ✓ implemented | `books.ts:10-11` rejects blank/non-string → 400 |
| R10 | GET /health endpoint | ✓ implemented | `books.ts:39-42` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — npm ci/build/start, env vars, route table |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `test(...)` blocks in `books.test.ts`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (test gate already ran the toolchain — not re-run):

```text
test_coverage = 1.0   → npm run build (tsc) + node --test dist/books.test.js passed
defect_rate   = 1.0   → build + tests succeeded
code_quality  = 0.7333
maintainability = 0.9037
idiomatic     = 0.85
```

Skip scan (`.skip(`/`xit`/`xdescribe`/`it.todo`): 0 — no disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: books.ts, server.ts, books.test.ts) | 200 |
| Source files (ts + config + README) | 6 |
| Dependencies (devDeps: @types/node, typescript) | 2 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Validation and error handling exceed the spec — safe-integer `year`, string `isbn`, 1 MiB body cap (413), 405 + Allow header
2. [info] Persistence round-trip tested across database reopen (`books.test.ts:67-87`)

No critical/high/medium/low findings. This is a clean, idiomatic implementation that satisfies every pinned requirement with zero runtime dependencies (uses built-in `node:sqlite` and `node:http`).

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (test gate)
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts"   # skip scan → 0
grep -cE "^test\(" books.test.ts      # test count → 5
# optional full re-run: npm ci && npm test
```
