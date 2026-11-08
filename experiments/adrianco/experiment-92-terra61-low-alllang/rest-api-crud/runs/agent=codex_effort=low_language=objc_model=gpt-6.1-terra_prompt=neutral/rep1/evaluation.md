# Evaluation: agent=codex_effort=low_language=objc_model=gpt-6.1-terra_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `clang -fobjc-arc -framework Foundation -lsqlite3` (test_coverage=1.0 from scores.json)
- **Lint:** pass — code_quality=0.78 from scores.json; built with `-Wall -Wextra`
- **Architecture:** single-file Objective-C HTTP server (`main.m`), raw BSD sockets + Foundation JSON + SQLite
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.m:40-47` INSERT, returns 201 with generated id |
| R2 | GET /books lists all books | ✓ implemented | `main.m:36-38` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.m:37-38` binds `author=?` when query present; test `test_crud_and_filter` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.m:38` returns row or 404 `Book not found` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.m:47` UPDATE, 404 when `sqlite3_changes==0` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.m:49` DELETE, 404 when no row |
| R7 | SQLite storage | ✓ implemented | `main.m:53` `CREATE TABLE … books`; `-lsqlite3` |
| R8 | JSON responses + status codes | ✓ implemented | `respond()` `main.m:13-18`; 200/201/400/404/405/413/500 |
| R9 | Validation: title & author required | ✓ implemented | `main.m:44` rejects non-string/blank title or author → 400; test `test_validation_and_missing` |
| R10 | GET /health | ✓ implemented | `main.m:33` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, env vars, API, curl examples |
| R12 | ≥3 tests | ✓ implemented | `test_books.py` 4 tests, all pass (test_coverage=1.0) |

## Build & Test

```text
clang -Wall -Wextra -Wno-unused-parameter -fobjc-arc -framework Foundation -lsqlite3 main.m -o books-server
python3 -m unittest -v test_books.py
test_crud_and_filter ... ok
test_health_and_empty_list ... ok
test_persistence ... ok
test_validation_and_missing ... ok
Ran 4 tests in 0.286s — OK
```

Scores read from `scores.json` (inline gate); build/test not re-run.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.m, non-blank) | 57 |
| Lines of code (test_books.py, non-blank) | 62 |
| Source files | 4 (main.m, test_books.py, Makefile, README.md) |
| Dependencies | 0 third-party (Foundation + system sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [info] TCP listener/accept loop is not exercised by tests — harness drives the handler via `BOOKS_TEST_FD` socketpair because the sandbox blocked binding localhost (`_agent_stdout.log` item_8). The HTTP request handler itself is fully covered end-to-end.
2. [info] Validation exceeds spec — year/isbn type checks, boolean rejection, 1 MiB body cap, Transfer-Encoding rejection.

## Notes

- The agent adapted `test_books.py` from a TCP-port harness to a `socketpair`-based one when the sandbox refused to bind localhost. This is a legitimate environment workaround (`main.m:54` `BOOKS_TEST_FD` path) that exercises the same `handle()` code; it is not a stubbed or skipped test. No requirement is weakened by it.
- Tight, idiomatic-for-C single file; `fobjc-arc` memory management; parameterized SQL throughout (no injection). idiomatic=0.30 from scores.json reflects the dense single-line style rather than any correctness issue.

## Reproduce

```bash
cd experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=objc_model=gpt-6.1-terra_prompt=neutral/rep1
make           # clang build
make test      # python3 -m unittest -v test_books.py
```
