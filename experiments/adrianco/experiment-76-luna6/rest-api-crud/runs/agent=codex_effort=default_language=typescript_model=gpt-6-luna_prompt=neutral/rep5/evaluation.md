# Evaluation: agent=codex language=typescript model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` in `scores.json` (build+tests ran green)
- **Lint:** unavailable — no linter configured; `code_quality=0.622` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Requirements are pinned by `rest-api-crud/REQUIREMENTS.json` (12 items) and used verbatim. The `neutral` prompt factor adds no extra checkable requirement beyond "include tests" (already R12). Scores read from `scores.json`; build/test/lint were not re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/server.ts:24-30` → `books.ts:45 create` |
| R2 | GET /books lists all books | ✓ implemented | `src/server.ts:23` → `books.ts:34 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:23` passes param; `books.ts:37` `WHERE author = ?` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/server.ts:35-38`, 404 on miss (`books.ts:41 get`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/server.ts:39-46` → `books.ts:51 update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/server.ts:47` → `books.ts:57 delete` |
| R7 | Data stored in SQLite | ✓ implemented | `books.ts:1,19-22` `node:sqlite` `DatabaseSync`, table DDL |
| R8 | JSON responses + status codes | ✓ implemented | `src/server.ts:4-7 send`; 201/200/404/400 across routes |
| R9 | Validation: title & author required | ✓ implemented | `books.ts:67-68 validateBook`; test `books.test.cjs:22-27` |
| R10 | GET /health | ✓ implemented | `src/server.ts:22` returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — install/build/start, endpoints, env vars |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 tests in `test/books.test.cjs`; `test_coverage=1.0` |

No requirements missing or partial. One quality note: the 3 tests target the `BookStore`/`validateBook` layer directly — the HTTP handler layer (`createApp` routing, status codes) is verified only indirectly (see `findings.jsonl` `test-http-layer`, low).

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json
test_coverage = 1.0   → build (tsc) + `node --test` passed, all tests green
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.6222
maintainability = 0.6133
idiomatic     = 0.68
token_efficiency = 0.0039
```

Skip scan: `grep` matched 1 line (`src/server.ts:57 process.exit(` matched `xit(`) — a false positive, not a test skip. Effective tests = 3.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 134 (src/books.ts 74, src/server.ts 60) |
| Test LOC | 48 |
| Files (excl. dist/node_modules) | 14 |
| Dependencies | 2 (both dev: typescript, @types/node) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] HTTP route layer not exercised by tests — `test/books.test.cjs` tests the store/validation layer directly, not `createApp()` routes/status codes.
2. [info] Robustness beyond spec — 1MB body cap, positive-integer id check, SIGINT/SIGTERM graceful shutdown.

No critical/high/medium findings. Spec-complete, dependency-light (zero runtime deps — built entirely on Node built-ins), tests green.

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep5"
cat scores.json                    # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json     # pinned 12-item checklist
# build + test (only if re-verifying; scores already stored):
# npm install && npm test
```
