# Evaluation: language=objc_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-opus-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 registered / all pass / 0 skipped (23 effective) — from `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests ran and passed)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session — see module notes below instead of `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

All mechanical scores come from the archive's `scores.json` (the DB row for this
cell was not queryable by status/config, so the just-computed inline scores were
used, per the skill's fastest-source path): `test_coverage=1.0`,
`code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.792`, `idiomatic=0.85`,
`token_efficiency=0.0101`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/BookRouter.m:133` handleCreateBook → `BookStore.m:125` INSERT, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `BookRouter.m:111` handleListBooks → `BookStore.m:169` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRouter.m:112`; `BookStore.m:180` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BookRouter.m:126` handleGetBook; `bookNotFound:` at :345 returns 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookRouter.m:157` handleReplaceBook → `BookStore.m:240` UPDATE |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookRouter.m:199` handleDeleteBook → `BookStore.m:288` DELETE, 204/404 |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore.m:24` sqlite3_open_v2, WAL, schema at :35 |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/204/400/404/405/500 across `BookRouter.m`; `HTTPResponse jsonResponseWithStatus:` |
| R9 | title & author required (400) | ✓ implemented | `BookRouter.m:231` validatePayload requireRequiredFields; `validationFailure:` → 400 at :351 |
| R10 | GET /health | ✓ implemented | `BookRouter.m:57,103` handleHealth pings DB, 200/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, build, run, endpoints); `Makefile` build/run/test targets |
| R12 | ≥ 3 tests | ✓ implemented | 23 tests registered (7 store + 8 router + 8 integration); `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` per the evaluate-run skill.

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0
=> build succeeded, all tests executed and passed, lint clean
```

```text
23 tests registered via TestSupport (custom harness; XCTest is unavailable
under Command Line Tools):
  StoreTests        7   (CRUD, filter, persistence across reopen, unicode, concurrency)
  RouterTests       8   (validation, PUT vs PATCH, status codes, query decode)
  IntegrationTests  8   (over-the-wire lifecycle, HEAD, concurrency, malformed input)
0 skipped (no XCTSkip/ignore markers found).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+tests, .m/.h) | 2314 |
| Files (excl. .git) | 29 |
| Dependencies | 0 third-party (Foundation + libsqlite3 only) |
| Tests total | 23 |
| Tests effective | 23 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] PATCH /books/{id} added beyond the PUT spec — correct superset
2. [info] Hand-rolled HTTP/1.1 server + mini test harness (no third-party framework)
3. [info] Low token efficiency / high LOC — inherent to objc without a web framework

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-46-opus5/bookshop/runs/language=objc_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                                   # mechanical scores (source of truth)
grep -rcE 'TestRegister\(' tests/*.m              # test counts per file (23 total)
grep -rnE 'XCTSkip|#\[ignore\]' tests/            # skip check (none)
make build && make test                           # optional: re-run the toolchain
```
