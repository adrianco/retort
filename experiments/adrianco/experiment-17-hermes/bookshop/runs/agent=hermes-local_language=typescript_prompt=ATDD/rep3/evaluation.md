# Evaluation: agent=hermes-local language=typescript prompt=ATDD · rep 3

## Summary

- **Factors:** language=typescript, agent=hermes-local (model qwen3-coder-30b), prompt=ATDD, framework=Express
- **Status:** failed (does not build; acceptance test suite never loads — stored mechanical scores are false positives)
- **Requirements:** 1/12 implemented, 11 partial, 0 missing (10 functional endpoints are coded but unbuildable/untested; see note)
- **Tests:** 1 passed / 0 failed / 0 skipped (1 effective) — but the 2 real API tests fail to load, so only a trivial `expect(1).toBe(1)` placeholder actually ran
- **Build:** fail — `tsc` cannot resolve `sqlite` (index.ts) or `./database`/`./routes/books` (server.ts). Stored `defect_rate=1.0` is not credible (the type-check tooling did not surface these — likely never ran).
- **Lint:** stored `code_quality=0.7333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (3 critical, 3 high, 1 medium, 1 low)

> **Note on stored scores.** `scores.json` reports `test_coverage=1.0` and `defect_rate=1.0`, which the evaluate-run rubric would read as "build + all tests pass." Static reading of the workspace contradicts both: the project has unresolved imports in every non-placeholder source file, and the acceptance suite never loads. The `test_coverage=1.0` is an artifact of the pass-rate fallback counting jest's `Tests: 1 passed, 1 total` line (the placeholder in `basic.test.ts`) while missing the suite-level load failure of `book.api.test.ts`. This run is scored as a **failure** on the evidence, not the number.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `src/index.ts:75` full handler + validation + insert — but never built/tested |
| R2 | GET /books lists all | ~ partial | `src/index.ts:41` returns all rows — untested |
| R3 | GET /books ?author= filter | ~ partial | `src/index.ts:46-48` `WHERE author LIKE ?` (substring) — untested |
| R4 | GET /books/{id} + 404 | ~ partial | `src/index.ts:59` returns book or 404 — untested |
| R5 | PUT /books/{id} update | ~ partial | `src/index.ts:97` updates + 404 — untested |
| R6 | DELETE /books/{id} | ~ partial | `src/index.ts:126` deletes + 404 on `changes===0` — untested |
| R7 | Data in SQLite | ~ partial | `src/index.ts:16-28` opens `./bookstore.db`, creates table — but `sqlite` dep missing, won't build |
| R8 | JSON + status codes | ~ partial | `src/index.ts` uses 200/201/400/404/500 with `res.json` — untested |
| R9 | Validation: title & author required | ~ partial | `src/index.ts:80-82,103-105` 400 when missing — untested |
| R10 | GET /health | ~ partial | `src/index.ts:36` (and `src/server.ts:16`) return `{status:'OK'}` — the /health acceptance test never runs |
| R11 | README with setup/run | ✓ implemented | `README.md:23-42` documents install/build/start/test |
| R12 | ≥3 tests that run | ~ partial | 3 `it` blocks authored, but only 1 (trivial placeholder) executes; the 2 API tests fail to load |

**Prompt-factor requirements (ATDD):**

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Executable acceptance tests through the public HTTP interface, atomic/independent, driving the implementation | ~ partial | `book.api.test.ts` uses supertest at the HTTP boundary (correct ATDD style) but never loads (`:2` wrong import), covers only 2 of the requirements, and shares a persistent DB rather than an empty service per test |

*Why "partial" and not "implemented" for R1–R10:* the endpoint logic is genuinely written and looks correct, but the rubric credits a requirement as implemented only when the code builds and tests exercise it. Here nothing builds (missing `sqlite` dependency; `server.ts` imports two files that don't exist) and no API test runs, so no functional behavior is verified.

## Build & Test

Build/test were **not re-run** — stored scores were read from `scores.json`. The failure determination is from static analysis of the workspace, which directly contradicts the stored `test_coverage`/`defect_rate` (see note above).

```text
scores.json
{"code_quality":0.7333, "token_efficiency":1.0, "test_coverage":1.0,
 "defect_rate":1.0, "maintainability":0.3624, "idiomatic":0.35}
```

```text
Static build breakage (would fail `tsc --noEmit`):
  src/index.ts:2   Cannot find module 'sqlite'      (not in package.json deps)
  src/server.ts:2  Cannot find module './database'  (file does not exist)
  src/server.ts:3  Cannot find module './routes/books' (dir does not exist)

Test execution reality (jest):
  basic.test.ts        1 passed  (expect(1).toBe(1) — verifies nothing)
  book.api.test.ts     suite fails to load: Cannot find module './src/index'
                       → its 2 tests (/health, POST /books) never run
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .ts) | 213 |
| Files (excl. node_modules) | 17 |
| Dependencies (package.json) | 11 |
| Tests authored (`it` blocks) | 3 |
| Tests effective (actually run) | 1 |
| Skip ratio | 0% (no genuine skips) |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] index.ts imports the `sqlite` package, which is not a dependency (`src/index.ts:2`)
2. [critical] server.ts imports non-existent `./database` and `./routes/books` (`src/server.ts:2-3`)
3. [critical] Acceptance suite `book.api.test.ts` fails to load — wrong import path (`src/__tests__/book.api.test.ts:2`)
4. [high] Stored `test_coverage=1.0` is a false positive — only a trivial placeholder test runs
5. [high] R12: fewer than 3 substantive tests actually run

## Reproduce

```bash
cd experiment-17-hermes/bookshop/runs/agent=hermes-local_language=typescript_prompt=ATDD/rep3
cat scores.json
find src -type f
grep -n "from 'sqlite'" src/index.ts        # missing dependency
grep -n "import" src/server.ts               # ./database, ./routes/books do not exist
grep -n "import app" src/__tests__/book.api.test.ts   # './src/index' wrong path
# (build/test intentionally NOT re-run; stored scores read from scores.json)
```
