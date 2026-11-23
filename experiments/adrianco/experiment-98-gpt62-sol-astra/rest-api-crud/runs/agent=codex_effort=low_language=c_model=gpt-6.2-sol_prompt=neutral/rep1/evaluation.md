# Evaluation: rest-api-crud · agent=codex effort=low language=c model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — 5 C in-process + 5 Python HTTP e2e
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass — code_quality=0.956 from scores.json (built `-Wall -Wextra -Wpedantic`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info enhancements)

Scores read from `scores.json` (inline gate output): test_coverage=1.0, defect_rate=1.0,
code_quality=0.956, maintainability=0.964, idiomatic=0.70, token_efficiency=0.040.
Build/tests were **not** re-run, per skill guidance.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.c:122` INSERT…RETURNING; `route` dispatches POST /books; `test_crud` |
| R2 | GET /books lists all books | ✓ implemented | `books.c:120-121` SELECT…ORDER BY id; `test_health`/`test_crud` |
| R3 | GET /books ?author= filter | ✓ implemented | `books.c:119-120` WHERE author=?; `route:238` reads `author`; `test_filter` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `books.c:131` SELECT WHERE id=?; 404 at `books.c:189-190`; `test_crud` |
| R5 | PUT /books/{id} updates | ✓ implemented | `books.c:125-127` UPDATE…RETURNING; `test_crud` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books.c:128-129` DELETE…RETURNING → 204; `test_crud` |
| R7 | Data stored in SQLite | ✓ implemented | `books.c:267-281` `open_database`/CREATE TABLE; `test_persistence` reopens DB file |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `reply` sets `application/json`; 201/200/204/400/404/405 mapped `books.c:182,190,198` |
| R9 | Validation: title & author required | ✓ implemented | `books.c:62-72` `required_text`; 400 at `books.c:145-152`; `test_validation` |
| R10 | GET /health | ✓ implemented | `books.c:219-226` returns 200 `{"status":"ok"}`; `test_health` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, endpoints, curl, tests |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 5 C tests + 5 Python tests; test_coverage=1.0 |

No `prompt`-factor requirements: `prompts/neutral.md` prescribes no methodology (no `P*` items).

## Build & Test

Not re-run — stored scores used (skill Step 2). Toolchain per `Makefile`:

```text
make            # cc -std=c11 -Wall -Wextra -Wpedantic $(pkg-config --cflags/--libs libevent json-c sqlite3)
make test       # builds book-api + test-books, runs ./test-books  -> "5 tests passed"
make test-http  # python3 test_books.py  -> 5 integration tests over a spawned server
```

```text
scores.json: test_coverage=1.0 (build + all tests passed), defect_rate=1.0, code_quality=0.956
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 598 (books.c 328, test_books.c 148, test_books.py 122) |
| Files (excl. build artifacts) | 6 tracked source/doc (books.c, test_books.c, test_books.py, Makefile, README.md, .gitignore) |
| Dependencies | 3 system libs (libevent, json-c, sqlite3) |
| Tests total | 10 (5 C + 5 Python) |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are info-level enhancements beyond the spec; none are defects (full list in `findings.jsonl`):

1. [info] 405 + `Allow` header on unsupported methods — exceeds R8
2. [info] `Location` header + `RETURNING` echo on create — exceeds R1/R8
3. [info] Validation stricter than required (nonblank strings, 32-bit year, null-able isbn, trailing-junk rejection) — exceeds R9

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build/test not re-run)
cat ../../../REQUIREMENTS.json  # pinned R1–R12 checklist
grep -nE "route|books\(|open_database|required_text" books.c
# Optional full rebuild (needs libevent/json-c/sqlite3 + pkg-config):
#   make test && make test-http
```
