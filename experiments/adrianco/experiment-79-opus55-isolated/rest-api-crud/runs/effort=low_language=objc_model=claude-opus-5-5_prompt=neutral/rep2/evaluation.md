# Evaluation: rest-api-crud · effort=low language=objc model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=objc, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective, 86 checks) — from the test runner's own tally; `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` / `defect_rate=1.0` from `scores.json` (build + all tests ran)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `{run_dir}/scores.json` (inline gate output): `code_quality=1.0`, `test_coverage=1.0`, `defect_rate=1.0`, `maintainability=0.826`, `idiomatic=0.83`, `token_efficiency=0.092`. Build/test/lint were **not** re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BooksAPI.m:189 createBook:` → `ValidateBook` → `BookStore.m:97 INSERT`; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `BooksAPI.m:180 listBooks:` → `BookStore.m:111 listBooksWithAuthor:` (author=nil) |
| R3 | GET /books ?author= filter | ✓ implemented | `BooksAPI.m:181 ParseQuery(query)[@"author"]`; `BookStore.m:113 WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `BooksAPI.m:199 getBook:`; 404 at `BooksAPI.m:203`; `testCreateAndGet`/`testNotFound…` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BooksAPI.m:207 updateBook:body:`; `BookStore.m:143 UPDATE …`; `testUpdate` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BooksAPI.m:224 deleteBook:` → `BookStore.m:159 DELETE`; returns 204; `testDelete` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore.m:2 #import <sqlite3.h>`; schema at `BookStore.m:18`; `-lsqlite3` in Makefile |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `BooksAPI.m APIResponse` + `HTTPServer.m:115 SendResponse` (Content-Type: application/json); 200/201/204/400/404/405/413 |
| R9 | Validation: title and author required | ✓ implemented | `BooksAPI.m:77 ValidateBook` rejects missing/blank title/author → 400; `testValidation` |
| R10 | GET /health endpoint | ✓ implemented | `BooksAPI.m:154 /health` → 200 `{"status":"ok"}`; `testHealth` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — build/run/test, env vars, API table, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_main.m` — 11 tests registered in runner (`test_main.m:326`); `test_coverage=1.0` |

No requirements missing or partial. No requirement was scored on a stub.

## Build & Test

Not re-run — stored scores used (per skill Step 2).

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=1.0
=> build succeeded, all tests executed and passed, lint clean
```

```text
Agent-reported (tests/test_main.m runner): "11 tests, 0 failed (86 checks, 0 failed)"
Skip scan: 0 skipped/disabled/xfail across tests/
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1089 (src 739 + tests 350) |
| Files | 8 (7 src incl. headers + 1 test) |
| Dependencies | 0 third-party (system: Foundation, libsqlite3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] HTTP hardening beyond spec — 405 `Allow` header, 413/431 size limits, Transfer-Encoding rejection (`HTTPServer.m:115-190`)
2. [info] Integration tests exercise real HTTP including a 20-way concurrency test (`test_main.m:228,296`)
3. [info] Handler exceptions mapped to 500 rather than dropping the connection (`HTTPServer.m:211-217`)
4. [info] All DB access serialized through one `@synchronized` store connection (`BooksAPI.m:143`) — correct; caps real read concurrency

No correctness, build, test, or requirement-coverage defects were found. This is a clean, complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=objc_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                    # stored mechanical scores (build/test/lint not re-run)
cat ../../../REQUIREMENTS.json     # pinned R1–R12 checklist
grep -rnE "skip|disabled|xfail" tests/ | wc -l   # 0 skips
# optional full rebuild (not required for scoring):
make test                          # clang build + self-contained runner: "11 tests, 0 failed"
```
