# Evaluation: agent=hermes-0222_language=typescript_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4 · rep 2

## Summary

- **Factors:** language=typescript, model=llamacpp/Holo4-35B-A3B, agent=hermes-0222, prompt=neutral, stack=holo4 (temp 0.6, top_p 0.95, top_k 20, rep_penalty 1.0, ctx 262144, threshold 0.9)
- **Status:** ok — agent completed (`finish_reason=stop`, 38 API calls, ~866K total tokens, mostly cache reads)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); P1 (neutral prompt: include tests) followed
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — `defect_rate=1.0`, `test_coverage=0.873` from `scores.json` (not re-run)
- **Build:** pass (derived from `defect_rate=1.0`)
- **Lint:** `code_quality=0.733`; `maintainability=0.769`, `idiomatic=0.55`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/routes/books.ts:35` → 201; test `tests/books.test.ts:35` |
| R2 | GET /books lists all | ✓ implemented | `src/routes/books.ts:18`; test `:89` |
| R3 | ?author= filter | ✓ implemented | `src/routes/books.ts:23-25` (exact match); test `:95` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/routes/books.ts:67`; tests `:113`, `:119` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/routes/books.ts:81` partial update; tests `:135`, `:145` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/routes/books.ts:136` → 204; tests `:163-177` |
| R7 | SQLite storage | ✓ implemented | `src/db.ts` better-sqlite3, file `books.db`, WAL |
| R8 | JSON + appropriate status codes | ✓ implemented | 200/201/204/400/404/409/500 JSON; JSON 404 fallback `src/app.ts:18` (gap: uncaught TypeError → default 500, see finding) |
| R9 | title/author required | ✓ implemented | `src/validation.ts:26-31`; tests `:49`, `:57` |
| R10 | GET /health | ✓ implemented | `src/app.ts:10`; test `:27` |
| R11 | README setup/run | ✓ implemented | `README.md` setup, dev/build/start, test, curl examples |
| R12 | ≥3 tests | ✓ implemented | 14 supertest integration tests, `defect_rate=1.0` |
| P1 | Include tests demonstrating requirements (neutral prompt) | ✓ implemented | every endpoint covered in `tests/books.test.ts` |

Beyond spec: duplicate-ISBN → 409 (tested), 404 JSON fallback, partial PUT updates.

## Build & Test

```text
Not re-run (skill step 2). scores.json:
{"code_quality": 0.733, "token_efficiency": 0.0085, "test_coverage": 0.873,
 "defect_rate": 1.0, "maintainability": 0.769, "idiomatic": 0.55}
retort.db could not be opened read-only (WAL; sqlite3 error 14) — scores.json used as the source.
```

```text
Agent's own report (_agent_stdout.log): `npm run build` compiles cleanly; all 14 tests pass.
grep for .skip( / xit( / xdescribe( / it.todo( in src/ tests/ → 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 262 (src/), 179 tests |
| Files | 5 source, 1 test |
| Dependencies | 2 runtime (express 5, better-sqlite3), 9 dev |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Non-string title/author/isbn crashes validation (`.trim()` on non-string) → non-JSON 500 instead of 400 — `src/validation.ts:26`
2. [low] Create requires year and isbn though spec only mandates title/author — `src/validation.ts:32-37`
3. [low] PUT accepts empty isbn — `src/validation.ts:42-55`
4. [low] Tests share and delete the server's `books.db` (no DB path override) — `src/db.ts:4`, `tests/books.test.ts:16`
5. [info] DB handle/rows typed `any` — `src/db.ts:6`

## Reproduce

```bash
cd "<run_dir>"
cat scores.json
cat ../../../../REQUIREMENTS.json ../../../../prompts/neutral.md
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src tests | wc -l
wc -l src/*.ts src/routes/*.ts tests/*.ts
```
