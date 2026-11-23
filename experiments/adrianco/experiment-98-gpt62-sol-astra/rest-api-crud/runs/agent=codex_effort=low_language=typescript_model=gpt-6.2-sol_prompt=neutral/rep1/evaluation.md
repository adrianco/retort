# Evaluation: agent=codex effort=low language=typescript model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ `tsc` build + `node --test` ran green (not re-run)
- **Lint:** n/a — `code_quality=0.7333` from `scores.json`
- **Architecture:** single-module HTTP server (`books.ts`) + entrypoint (`index.ts`); run-summary skill not available in this environment
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.ts:91-96` INSERT … RETURNING, 201 + `Location` |
| R2 | GET /books lists all books | ✓ implemented | `books.ts:87-89` `list.all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `books.ts:88-89` `listByAuthor.all(author)`; test `books.test.ts:126` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `books.ts:109-112` `find.get(id)`, 404 when missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `books.ts:114-118` UPDATE … RETURNING |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `books.ts:120-123` `remove.run(id)`, 204 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `books.ts:2,59-68` `node:sqlite` `DatabaseSync`, CREATE TABLE; persistence test `books.test.ts:167` |
| R8 | JSON responses with correct HTTP status codes | ✓ implemented | `books.ts:17-20` `json()`; 201/200/204/400/404/405/413/500 throughout |
| R9 | Validation: title & author required | ✓ implemented | `books.ts:45-47` rejects non-string/empty → 400; test `books.test.ts:141` |
| R10 | GET /health health-check | ✓ implemented | `books.ts:80-81` returns `{status:'ok'}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md:7-15` npm ci/build/start + test |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `books.test.ts` — 5 tests, `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill policy.

```text
scores.json: {"code_quality":0.7333, "test_coverage":1.0, "defect_rate":1.0,
              "maintainability":0.7583, "idiomatic":0.85, "token_efficiency":0.0144}
```

`test_coverage=1.0` ⇒ `npm test` (`tsc` build then `node --test dist/books.test.js`) built and passed all tests. `defect_rate=1.0` confirms build+test success. The agent initially attempted an Express stack but the npm cache was offline (`_agent_stdout.log`), so it fell back to the Node built-in `node:http` + `node:sqlite` with zero runtime dependencies.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: books.ts + index.ts) | 158 |
| Lines of code (test: books.test.ts) | 188 |
| Files (excl. node_modules/.npm-cache/logs) | 14 |
| Dependencies (runtime) | 0 |
| Dependencies (dev: typescript, @types/node) | 2 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

None. All 12 pinned requirements implemented, tests pass, no skipped/disabled tests, no build/lint failures.

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6.2-sol_prompt=neutral/rep1
cat scores.json                 # stored mechanical scores (build/test not re-run)
grep -rE "\.skip\(|xit\(|it\.todo\(" . --include="*.ts" | wc -l   # 0 skips
grep -cE "^test\(" books.test.ts  # 5 tests
```
