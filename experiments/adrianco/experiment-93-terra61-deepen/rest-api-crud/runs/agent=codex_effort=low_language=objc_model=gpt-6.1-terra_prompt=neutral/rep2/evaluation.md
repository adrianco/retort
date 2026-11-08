# Evaluation: agent=codex effort=low language=objc model=gpt-6.1-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=objc, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `clang -fobjc-arc ... -framework Foundation -lsqlite3` (test_coverage=1.0 from scores.json implies build+test success)
- **Lint:** pass — code_quality=0.78 from scores.json (build uses `-Wall -Wextra`)
- **Architecture:** single-file Foundation + BSD-socket HTTP server backed by SQLite; see notes below (run-summary skill not available in this environment)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.m:104-113` INSERT INTO books, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `main.m:96,99,102` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.m:92-98` parses author query, `WHERE author = ?`; test `test_books.py:50-53` |
| R4 | GET /books/{id} by id | ✓ implemented | `main.m:83-102`; 404 when absent `main.m:101` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.m:104-113` UPDATE; 404 on no-change `main.m:111` |
| R6 | DELETE /books/{id} | ✓ implemented | `main.m:115-120` DELETE, 404 if no rows `main.m:119` |
| R7 | Data in SQLite | ✓ implemented | `main.m:124-126` sqlite3_open + CREATE TABLE; test `test_books.py:72-77` reads the db file |
| R8 | JSON + correct status codes | ✓ implemented | `reply()`/`errorReply()` `main.m:11-20`; 201/200/400/404/405/413/500 used throughout |
| R9 | title & author required | ✓ implemented | `validBook()` `main.m:29-43` rejects blank/non-string; tests `test_books.py:64-68` |
| R10 | GET /health | ✓ implemented | `main.m:81` returns `{"status":"ok"}`; test `test_books.py:41-42` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-27` (build, run, env vars, curl examples) |
| R12 | >= 3 tests | ✓ implemented | 4 test methods in `test_books.py`; test_coverage=1.0 |

## Build & Test

```text
make            # clang -Wall -Wextra -fobjc-arc main.m -o books -framework Foundation -lsqlite3
# test_coverage=1.0 / defect_rate=1.0 (scores.json) => build succeeded, all tests pass
```

```text
make test       # python3 -m unittest -v test_books.py
# 4 tests: test_health, test_crud_and_filter, test_validation, test_persistence — 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 137 (main.m) + 81 (test_books.py) |
| Files | main.m, test_books.py, Makefile, README.md |
| Dependencies | system only (Foundation, libsqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build | pass |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Server handles one connection at a time — acceptable and documented
2. [info] author filter is exact/case-sensitive match — spec-compliant

No defects, missing requirements, or skipped tests. The implementation goes beyond spec with request hardening (Content-Length validation, 64 KiB cap at `main.m:76`, chunked transfer-encoding rejection at `main.m:69`, SIGPIPE handling).

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=objc_model=gpt-6.1-terra_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (do not re-run build/test)
grep -cE "def test_" test_books.py
grep -rE "skip|xfail" test_books.py | wc -l
```
