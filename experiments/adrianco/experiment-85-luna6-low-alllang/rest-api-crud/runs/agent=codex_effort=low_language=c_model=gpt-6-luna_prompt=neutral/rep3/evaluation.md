# Evaluation: agent=codex effort=low language=c model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=c, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — the one `SkipTest` is a conditional guard for unavailable network binding, not a static skip
- **Build:** pass — `cc -O2 -Wall -Wextra -Wpedantic` (test_coverage=1.0 from scores.json implies build+tests passed)
- **Lint:** pass — code_quality=0.78 from scores.json; compiled with `-Wall -Wextra -Wpedantic`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.c:88-93` INSERT + returns 201 with the row |
| R2 | GET /books lists all books | ✓ implemented | `server.c:78-87` builds JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `server.c:80-83` parses `author=` and binds `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `server.c:97` SELECT by id, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.c:98-99` UPDATE, 404 if no row changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.c:100` DELETE, 404 if no row changed |
| R7 | Data stored in SQLite | ✓ implemented | `server.c:112` CREATE TABLE books; prepared statements throughout |
| R8 | JSON responses + HTTP status codes | ✓ implemented | 201/200/400/404/413/500 (`server.c:88-110`); `Content-Type: application/json` |
| R9 | Validation: title and author required | ✓ implemented | `server.c:91` rejects empty title/author with 400; test `test_api.py:71` |
| R10 | GET /health | ✓ implemented | `server.c:77` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, env vars, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_api.py` — 4 test methods, test_coverage=1.0 |

## Build & Test

Build/test were not re-run — stored mechanical scores are authoritative.

```text
# from scores.json
test_coverage=1.0   -> build succeeded AND all tests passed
defect_rate=1.0     -> build+test succeeded
code_quality=0.78
maintainability=0.67
idiomatic=0.30
```

```text
make test  (not re-run)
  python3 -m unittest -v test_api.py
  4 test methods: health+validation, create/list/filter/get, update/delete, sqlite storage
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: server.c) | 113 |
| Lines of code (tests: test_api.py) | 116 |
| Files (source: server.c, test_api.py, Makefile, README.md) | 4 |
| Dependencies | 1 system lib (libsqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] README lists "SQLite development library" twice (`README.md:8-9`)
2. [info] Hand-rolled JSON parser accepts only flat string/int fields (`server.c:43,56`)
3. [info] Server is single-threaded and blocking (`server.c:113`)

No requirement is missing or partial; no critical/high/medium findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                 # stored mechanical scores (build/test authoritative)
cat ../../../REQUIREMENTS.json  # pinned 12-requirement checklist
make            # cc -O2 -Wall -Wextra -Wpedantic -o book_service server.c -lsqlite3
make test       # python3 -m unittest -v test_api.py
```
