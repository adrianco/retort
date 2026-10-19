# Evaluation: agent=hermes-0222_language=typescript_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4 · rep 1

## Summary

- **Factors:** language=typescript, model=llamacpp/Holo4-35B-A3B, agent=hermes-0222, prompt=neutral, stack=holo4 (framework: Express + better-sqlite3)
- **Effective sampling:** temperature=0.6, top_p=0.95, top_k=20, repetition_penalty=1.0; context_length=262144, context_threshold=0.9 (`_effective_stack.json`)
- **Status:** ok — `_meta.json` succeeded=true; agent exited on `text_response(finish_reason=stop)` after 53 API calls
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); P1 (include tests demonstrating requirements) followed
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — `defect_rate=1.0` from `scores.json`
- **Build:** pass (tsc + ts-jest, derived from `defect_rate=1.0`; not re-run)
- **Lint:** code_quality=0.733 — minor warnings (shadowed import, CommonJS `require` in TS)
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 4 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/routes.ts:9-27`; test `creates a book and returns 201` |
| R2 | GET /books lists all | ✓ implemented | `src/routes.ts:30-43`; test `lists all books` |
| R3 | ?author= filter | ✓ implemented | `src/routes.ts:34-36` (exact match); test `filters by author` |
| R4 | GET /books/{id} | ✓ implemented | `src/routes.ts:46-53`, 404 via handleError; tests at `books.test.ts:160,167` |
| R5 | PUT /books/{id} | ✓ implemented | `src/routes.ts:56-94` partial update, 404/400/409; test `updates a book` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/routes.ts:97-106` returns 204; tests at `books.test.ts:191,196` |
| R7 | SQLite storage | ✓ implemented | `src/database.ts:1-19` better-sqlite3, file `books.db` |
| R8 | JSON + proper status codes | ✓ implemented | 201/200/204/400/404/409 throughout `src/routes.ts`; malformed JSON → 500 (see findings) |
| R9 | title & author required | ✓ implemented | `src/middleware.ts:7-13`; tests `returns 400 for missing title/author` |
| R10 | GET /health | ✓ implemented | `src/index.ts:12-14`; test `returns 200 with status ok` |
| R11 | README setup/run | ✓ implemented | `README.md:14-33` |
| R12 | ≥3 tests | ✓ implemented | 14 `it()` cases in `src/__tests__/books.test.ts`; defect_rate=1.0 |
| P1 | Tests demonstrate requirements (neutral prompt) | ✓ followed | every endpoint has at least one test |

Enhancements beyond spec: duplicate-ISBN 409, partial-update validation, year range check.

## Build & Test

```text
Not re-run (per skill). Stored scores from scores.json:
defect_rate=1.0  test_coverage=0.5328  code_quality=0.7333
maintainability=0.8333  idiomatic=0.0  token_efficiency=0.0049
```

```text
npm test (jest) — agent-reported and confirmed by defect_rate=1.0: 14 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, excl. tests) | 295 |
| Lines of test code | 201 |
| Files (src) | 6 |
| Dependencies | 2 runtime, 8 dev |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |
| Agent tokens | 1,747,114 total (37,753 in / 21,162 out / 1,688,199 cache-read), 53 calls |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Malformed JSON body returns 500 instead of 400 — `src/middleware.ts:79`
2. [medium] POST/PUT without JSON Content-Type crash with 500 — `src/middleware.ts:82`, `:7`
3. [low] Tests re-wire their own app instead of exercising `src/index.ts` (which listens at import)
4. [low] Tests are order-dependent on shared DB state (id 1)
5. [low] Shadowed `path` import / CommonJS `require` in TS — `src/database.ts:3,27,43`

Note: `idiomatic=0.0` (haiku cache) looks like a scorer default rather than a genuine judgement of this code — treat that metric with suspicion for this run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-91-holo4-screen/rest-api-crud/runs/agent=hermes-0222_language=typescript_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep1"
cat scores.json
cat ../../../../REQUIREMENTS.json
grep -rcE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src
# (optional, in a temp copy) npm install && npm test
```
