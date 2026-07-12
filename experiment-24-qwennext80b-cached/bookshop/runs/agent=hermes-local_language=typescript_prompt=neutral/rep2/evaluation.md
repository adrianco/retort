# Evaluation: agent=hermes-local language=typescript prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local, framework=unknown (Express), prompt=neutral
- **Status:** ok (spec largely met) — one core technical constraint (SQLite) unmet
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R7 SQLite/embedded DB)
- **Tests:** 25 test cases present (12 unit + 13 integration), 0 skipped; stored test_coverage=0.1761 (low — integration suite shares state and likely fails count assertions)
- **Build:** pass — defect_rate=1.0 from scores.json (build+test executed)
- **Lint:** pass — code_quality=0.7333 from scores.json
- **Architecture:** see `summary/index.md` — clean layered Express (routes → controller → repository → store)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 2 high, 0 medium, 2 low, 1 info)

Scores read from `scores.json` (not re-run): code_quality=0.7333, token_efficiency=1.0, test_coverage=0.1761, defect_rate=1.0, maintainability=0.8488, idiomatic=0.38.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/routes/books.ts:9`, `BookController.create` (`controllers/BookController.ts:31`), returns 201 |
| R2 | GET /books lists all | ✓ implemented | `BookController.getAll` (`controllers/BookController.ts:15`) |
| R3 | GET /books ?author= filter | ✓ implemented | `controllers/BookController.ts:9-13` → `getByAuthor` (`database/Database.ts:46`) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `controllers/BookController.ts:19-29` |
| R5 | PUT /books/{id} update | ✓ implemented | `controllers/BookController.ts:36-46` |
| R6 | DELETE /books/{id} | ✓ implemented | `controllers/BookController.ts:48-58` (204/404) |
| R7 | Data stored in SQLite / embedded DB | ✗ missing | `database/Database.ts:17` in-memory `BookRow[]`; default `:memory:`; no sqlite dep in `package.json` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204/500 across controller + `app.ts:14-17` |
| R9 | Validation: title & author required | ✓ implemented | `models/Book.ts:35-40`, `middleware/validation.ts:4-11` (over-strict; see findings) |
| R10 | GET /health | ✓ implemented | `app.ts:8-10` |
| R11 | README with setup/run | ✓ implemented | `README.md` (install/build/run/env/endpoints) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 25 cases in `tests/`; test_coverage=0.1761 > 0 |

## Build & Test

Not re-run (per skill; stored scores used).

```text
scores.json → defect_rate=1.0 (build+test executed), test_coverage=0.1761
25 test cases (unit.test.ts: 12, integration.test.ts: 13), 0 skipped
```

The low test_coverage is explained by a shared-state defect: `integration.test.ts` uses the
module-singleton `db` (`Database.ts:95`) with no per-test reset, so absolute-count assertions
(`length toBe(2)` at `integration.test.ts:114`, author filter at `:135`) observe accumulated
books from earlier POST tests and fail.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src, .ts) | 334 |
| Lines of code (tests, .ts) | 372 |
| Files (src+tests) | 11 |
| Dependencies (deps+devDeps) | 10 |
| Tests total | 25 |
| Tests effective | 25 (0 skipped) |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R7 — No SQLite/embedded DB; storage is a plain in-memory array (`Database.ts:17-95`)
2. [high] Integration tests share a module-singleton DB with no reset → order-dependent count assertions fail (`integration.test.ts:114`)
3. [low] POST /books over-validates — rejects missing year/isbn though only title+author required (`models/Book.ts:43-49`)
4. [low] Unused, mismatched jest mock references a nonexistent SQLite API (`tests/__mocks__/database.ts:3-13`)
5. [info] Low idiomatic score (0.38) — hand-rolled persistence, pass-through repository

## Reproduce

```bash
cd "experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json  # pinned 12-requirement checklist
find src tests -name '*.ts' | xargs wc -l
grep -riE "sqlite|better-sqlite" package.json   # only the keyword, no dependency
```
