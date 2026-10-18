# Evaluation: agent=codex effort=low language=c model=gpt-6-luna prompt=neutral · rep 1

> **SECOND OPINION.** This re-checks a prior evaluation that scored
> `requirement_coverage=0.9167` and flagged **R4** (GET /books/{id}) as not met.
> **Verdict: the first evaluator was CORRECT.** R4 is genuinely broken — the
> get-by-id route always returns 404, including for existing books. Verified by
> reading `book_service.c:34` and by an empirical SQLite probe (see below).
> Final `requirement_coverage` is unchanged at **0.9167 (11/12)**.

## Summary

- **Factors:** language=c, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (builds and tests pass; one route is functionally broken)
- **Requirements:** 11/12 implemented, 1 partial (R4), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — but handler layer untested
- **Build:** pass — `test_coverage=1.0` from scores.json
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 1 medium)

## Re-check of the disputed claim (R4)

First evaluator's evidence: *"book_service.c:34 — books_json(st,&b,0) steps the
statement to SQLITE_DONE, then sqlite3_data_count(st) is checked; it returns 0
after SQLITE_DONE so `found` is always 0 and the handler always returns 404."*

Confirmed. `book_service.c:34`:

```c
books_json(st,&b,0);
int found=sqlite3_data_count(st)>0;
...
if(!found){free(b.data);return error(c,404,"book not found");}
```

`books_json` (`book_service.c:23`) runs `while(sqlite3_step(st)==SQLITE_ROW){...}`,
so on return the last step was `SQLITE_DONE`. Per SQLite semantics
`sqlite3_data_count()` returns 0 after `SQLITE_DONE`, so `found` is always 0.

Empirical probe (standalone, one matching row inserted, mimicking the handler):

```text
rows stepped=1  data_count after loop=0  found=0
```

The book JSON *was* assembled into `b`, but the always-false `found` check throws
it away and returns 404. The 404-when-absent behaviour is correct only by
coincidence; the fetch-one-book path never succeeds. **R4 not met — partial**
(route + 404-absent path present, core get-by-id broken).

Why `test_coverage=1.0` did not catch it: the tests (`test_api.c`) never call
`handler()` — they exercise `execute_book()`/SQLite directly — so no test issues a
`GET /books/{id}`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_service.c:31-33` INSERT + 201 w/ body |
| R2 | GET /books lists all | ✓ implemented | `book_service.c:30` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `book_service.c:30` `WHERE author=?` |
| R4 | GET /books/{id} single book | ~ partial | `book_service.c:34` always 404 (data_count after SQLITE_DONE) |
| R5 | PUT /books/{id} updates | ✓ implemented | `book_service.c:36` UPDATE, preserves omitted fields |
| R6 | DELETE /books/{id} | ✓ implemented | `book_service.c:35` DELETE + sqlite3_changes→404 |
| R7 | SQLite storage | ✓ implemented | `book_service.c:3,42` sqlite3_open + CREATE TABLE |
| R8 | JSON + status codes | ✓ implemented | `respond`/`error` set JSON content-type; 201/200/404/400/413 |
| R9 | title+author required | ✓ implemented | `book_service.c:32` 400 if missing |
| R10 | GET /health | ✓ implemented | `book_service.c:29` `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` build/run/API/tests sections |
| R12 | ≥3 tests | ✓ implemented | `test_api.c` 3 tests; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage=1.0   defect_rate=1.0   maintainability=1.0   code_quality=0.956
idiomatic=0.12      token_efficiency=0.0049
```

3 tests (`test_json_escaping`, `test_request_fields`,
`test_sqlite_crud_and_author_filter`), 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Source files | book_service.c, test_api.c, Makefile, README.md |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| test_coverage | 1.0 |
| code_quality | 0.956 |

## Findings

1. [high] R4 — GET /books/{id} always returns 404, even for existing books (`book_service.c:34`)
2. [medium] Unit tests never exercise the HTTP handler, so the R4 regression passes undetected (`test_api.c:25-41`)

## Reproduce

```bash
# R4 verification probe (SQLite data_count after loop)
cat > /tmp/probe.c <<'EOF'
#include <sqlite3.h>
#include <stdio.h>
int main(){sqlite3*db;sqlite3_open(":memory:",&db);
 sqlite3_exec(db,"CREATE TABLE books(id INTEGER PRIMARY KEY,title TEXT)",0,0,0);
 sqlite3_exec(db,"INSERT INTO books VALUES(1,'Dune')",0,0,0);
 sqlite3_stmt*st;sqlite3_prepare_v2(db,"SELECT id,title FROM books WHERE id=?",-1,&st,0);
 sqlite3_bind_int64(st,1,1);int n=0;while(sqlite3_step(st)==SQLITE_ROW)n++;
 printf("rows=%d data_count=%d found=%d\n",n,sqlite3_data_count(st),sqlite3_data_count(st)>0);
 return 0;}
EOF
cc /tmp/probe.c -lsqlite3 -o /tmp/probe && /tmp/probe   # -> rows=1 data_count=0 found=0
```
