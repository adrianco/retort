# Evaluation: agent=codex effort=low language=c model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`)
- **Tests:** 4 test methods, all passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0`
- **Build:** pass (from `scores.json`: `test_coverage=1.0 ⇒ build + tests passed`)
- **Lint:** pass — `code_quality=0.956` (compiled with `-Wall -Wextra -Wpedantic`)
- **Architecture:** run-summary skill unavailable in this session — summarized inline below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Single-file libevent + json-c + SQLite C11 HTTP service (`books.c`, 230 LoC) with an
in-process handler test harness (`test_handler.c`) driving the real `handle()` callback
against temporary SQLite databases from a Python `unittest` suite.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books.c:116-117` INSERT…RETURNING, `bind_book` 67-80, 201 at 147 |
| R2 | GET /books lists all books | ✓ implemented | `books.c:114-115` SELECT … ORDER BY id, array build 163-168 |
| R3 | GET /books ?author= filter | ✓ implemented | `books.c:115` `WHERE (?1 IS NULL OR author=?1)`, param read 158-159; `test_books.py:83-88` |
| R4 | GET /books/{id} single book | ✓ implemented | `books.c:125` SELECT WHERE id=?1, 404 on no row 173 |
| R5 | PUT /books/{id} updates | ✓ implemented | `books.c:127-128` UPDATE…RETURNING; `test_books.py:74-77` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books.c:126` DELETE…RETURNING; `test_books.py:78-81` |
| R7 | Data stored in SQLite | ✓ implemented | `books.c:192-204` open_database + CREATE TABLE books, file-backed `books.db` 213 |
| R8 | JSON responses + correct status codes | ✓ implemented | `reply` 18-29 sets `application/json`; 201/200/404/400/405/500 across handler |
| R9 | Validation: title and author required | ✓ implemented | `valid_text(title,1)`/`valid_text(author,1)` 72 → 400 at 143; `test_books.py:90-100` |
| R10 | GET /health | ✓ implemented | `books.c:107-110` returns `{"status":"ok"}`; `test_books.py:103` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:1-45` deps, build, run, API, tests |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_books.py` 4 methods (CRUD, filter, validation, health/routing), `test_coverage=1.0` |

## Build & Test

```text
make            # cc -O2 -g -std=c11 -Wall -Wextra -Wpedantic (libevent json-c sqlite3)
# Not re-run — test_coverage=1.0 in scores.json ⇒ build + all tests passed
```

```text
make test       # python3 -m unittest -v test_books
# 4 tests, 0 failures, 0 skips (test_coverage=1.0 from scores.json)
```

Stored scores (`scores.json`): `test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.956`,
`maintainability=0.767`, `idiomatic=0.82`, `token_efficiency=0.024`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 371 (books.c 230, test_handler.c 35, test_books.py 106) |
| Files (source) | 5 (books.c, test_handler.c, test_books.py, Makefile, README.md) |
| Dependencies | 3 (libevent, json-c, sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored pass) |

## Findings

Top items (full list in `findings.jsonl`) — all informational; no defects found:

1. [info] POST returns 201 with a Location header (beyond spec) — `books.c:174-178`
2. [info] Unsupported methods return 405 with Allow header — `books.c:131-134`
3. [info] Atomic validation: malformed bodies never partially mutate — `test_books.py:90-100`
4. [info] Default `make test` drives handler in-process; TCP mode via `BOOKS_TEST_TCP=1` — `Makefile:9-10`

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                       # stored build/test/lint scores (do not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-item checklist
grep -cE 'def test_' test_books.py    # test count
make && make test                     # only if re-verifying from scratch
```
