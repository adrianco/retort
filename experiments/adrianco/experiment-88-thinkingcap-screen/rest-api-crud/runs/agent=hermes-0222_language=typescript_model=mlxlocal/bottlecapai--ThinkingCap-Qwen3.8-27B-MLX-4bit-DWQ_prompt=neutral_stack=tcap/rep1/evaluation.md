# Evaluation: agent=hermes-0222_language=typescript_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap · rep 1

## Summary

- **Factors:** language=typescript, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, agent=hermes-0222, prompt=neutral, stack=tcap
- **Status:** ok (`_meta.json` succeeded=true)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); P1 (neutral prompt: include tests demonstrating requirements) followed
- **Tests:** 21 passed / 0 failed / 0 skipped (21 effective) — test_coverage=1.0 from `scores.json`
- **Build:** pass (defect_rate=1.0, test_coverage=1.0 from `scores.json`; agent's `hermes verify` reports tsc build pass) — not re-run
- **Lint:** code_quality=0.733 (from `scores.json`); maintainability=0.691, idiomatic=0.8
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/app.ts:164-175` INSERT, 201; test `creates a book and returns 201` |
| R2 | GET /books lists all | ✓ implemented | `src/app.ts:177-192`; test `lists all books` |
| R3 | ?author= filter | ✓ implemented | `src/app.ts:180-185` `WHERE author = ?`; test `filters by ?author=` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/app.ts:194-204`; tests `returns a single book by id`, `returns 404 for a nonexistent id` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:206-229` partial update; test `updates provided fields` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.ts:231-239` 204/404; test `deletes a book (204) and it is gone afterwards` |
| R7 | SQLite storage | ✓ implemented | `src/db.ts` better-sqlite3, file DB `books.db` by default (`src/server.ts:4`) |
| R8 | JSON + proper status codes | ✓ implemented | 200/201/204/400/404/500 with JSON errors, `src/app.ts:241-259` |
| R9 | title & author required | ✓ implemented | `src/app.ts:40-45`; tests `rejects a missing title/author with 400` |
| R10 | GET /health | ✓ implemented | `src/app.ts:160-162`; test `returns 200 with status ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup / Run / Tests sections |
| R12 | ≥3 tests | ✓ implemented | 21 vitest tests in `tests/books.test.ts`, test_coverage=1.0 |
| P1 | Tests demonstrate requirements (neutral prompt) | ✓ implemented | every endpoint + validation covered in `tests/books.test.ts` |

Beyond spec: malformed-JSON → 400, malformed id → 400, empty PUT body → 400, JSON 404 for unknown routes, `PORT`/`DB_PATH` env config.

## Build & Test

```text
(not re-run — scores read from scores.json)
test_coverage=1.0  defect_rate=1.0  code_quality=0.7333  maintainability=0.6913  idiomatic=0.8
Agent's own verify (_agent_stdout.log): bootstrap pass, tsc build pass, vitest 21/21 pass, readiness probe on :8000 pass
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 307 (src/app.ts 262, src/db.ts 35, src/server.ts 10) |
| Test lines | 219 |
| Files (excl. node_modules, summary, _judge) | 18 |
| Dependencies | 8 (2 runtime, 6 dev) |
| Tests total | 21 |
| Tests effective | 21 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [low] `validateCreate` doc comment says all four fields are required, but year/isbn are optional (`src/app.ts:28`)
2. [info] `?author=` filter is exact, case-sensitive match (`src/app.ts:183`)
3. [info] PUT checks existence before validating the body (`src/app.ts:208-216`)

## Reproduce

```bash
cd <run_dir>
cat scores.json
npm install && npm test
```
