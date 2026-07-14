# Evaluation: language=typescript_model=sonnet-4.6_prompt=tdd · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet-4.6, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json) + 4/4 prompt instructions followed
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — via `test_coverage=1.0` (build+tests) from scores.json
- **Lint:** n/a — `code_quality=0.733` from scores.json (no separate linter re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:33` INSERT + re-select, 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:48` SELECT * |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:51-52` WHERE author = ? |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:59` + 404 at :63 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:70` UPDATE, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:96` DELETE, 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `better-sqlite3`, `src/app.ts:12` schema |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404 across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `src/app.ts:35,72` → 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:29` → {status:"ok"} |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` (setup/run/test/endpoints) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `src/api.test.ts` 13 tests, test_coverage=1.0 |

### Prompt instructions (prompt=tdd)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Write failing test before implementation | ✓ followed | agent log: "Red — wrote all tests referencing ./app… confirmed they failed" |
| P2 | Minimum code to pass each test | ✓ followed | agent log: "Green — implemented buildApp with minimum code" |
| P3 | Refactor after green without adding behaviour | ✓ followed | agent log: "Refactor — no structural issues found" |
| P4 | Keep red/green/refactor tight, no skipping ahead | ✓ followed | 13 tests map 1:1 to implemented routes/cases; DI factory testable |

## Build & Test

Build/test were not re-run — stored mechanical scores from `scores.json` are authoritative:

```text
test_coverage = 1.0   → build compiled (tsc) + all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.7333
maintainability = 0.7624
idiomatic     = 0.78
token_efficiency = 1.0
```

```text
# test command (jest via ts-jest), reported by agent: 13 tests, all green
src/api.test.ts: GET /health, POST /books (3), GET /books (2),
                 GET /books/:id (2), PUT /books/:id (3), DELETE /books/:id (2)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 269 (app 109, tests 150, server 10) |
| Files | 14 (excl. node_modules) |
| Dependencies | 12 (2 runtime, 10 dev) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] ?author= filter is exact-match only — `src/app.ts:52`
2. [info] PUT requires full body (title+author), no PATCH semantics — `src/app.ts:72`
3. [info] No numeric/format validation on year/isbn — `src/app.ts:34`

No critical, high, or medium findings. All requirements and prompt instructions satisfied.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=typescript_model=sonnet-4.6_prompt=tdd/rep1
cat scores.json            # authoritative build/test/lint scores
npm install && npm test    # optional: re-run 13 jest tests
```
