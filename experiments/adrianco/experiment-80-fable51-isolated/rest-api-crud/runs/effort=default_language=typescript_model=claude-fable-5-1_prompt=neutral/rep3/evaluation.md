# Evaluation: effort=default_language=typescript_model=claude-fable-5-1_prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ build + all tests ran (tsx/tsc toolchain; not re-run)
- **Lint:** pass — `code_quality=0.7333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:13-21` → `db.ts:29-34`; test `books.test.ts:45` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:23-30` → `db.ts:36-43`; test `books.test.ts:82` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/db.ts:39-41` (`WHERE author = ? COLLATE NOCASE`); test `books.test.ts:90-95` |
| R4 | GET /books/{id} single book, 404 | ✓ implemented | `src/app.ts:32-40`; test `books.test.ts:98-109` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:42-59` → `db.ts:52-57`; test `books.test.ts:111-125` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:61-68` → `db.ts:59-61`; test `books.test.ts:127-134` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/db.ts:1,14-27` (`node:sqlite` `DatabaseSync`); file-persistence test `books.test.ts:143-159` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/400/404 across `src/app.ts`; error handler `app.ts:74-82` |
| R9 | Input validation: title + author required | ✓ implemented | `src/validation.ts:14-19`; test `books.test.ts:58-67` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:9-11`; test `books.test.ts:39-43` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` (Requirements/Setup/Run/build/start sections) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 12 `it(...)` cases, `test_coverage=1.0` |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and only asks for tests demonstrating the requirements — satisfied by the 12-case suite; no additional `P*` requirements.

## Build & Test

Build and tests were **not re-run** — stored mechanical scores were used per the evaluate-run skill.

```text
scores.json
test_coverage = 1.0   (build + all tests executed and passed)
defect_rate   = 1.0   (build+test succeeded)
code_quality  = 0.7333
maintainability = 0.7263
idiomatic     = 0.82
token_efficiency = 0.0595
```

```text
npm test  ->  tsx --test tests/*.test.ts
12 it(...) cases, 0 skipped  (grep: 0 .skip/xit/xdescribe/it.todo)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 204 (src/*.ts); 364 incl. tests |
| Files (excl. node_modules/lock/agent logs) | 15 |
| Dependencies | 5 (1 runtime: express; 4 dev) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no defects:

1. [info] Case-insensitive `?author=` filter (`src/db.ts:40`)
2. [info] Dedicated malformed-JSON 400 handler (`src/app.ts:74-82`)
3. [info] Persistence verified on a file-backed DB (`tests/books.test.ts:143-159`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=typescript_model=claude-fable-5-1_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/quality scores
cat ../../../REQUIREMENTS.json                    # pinned R1–R12 checklist
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src tests --include="*.ts" | wc -l   # 0
grep -rEn "\bit\(" tests --include="*.ts" | wc -l # 12
# (build/tests not re-run: test_coverage=1.0 in scores.json already proves build+test)
```
