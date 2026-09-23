# Evaluation: effort=low language=c model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 checks / 5 test functions, all pass (0 skipped, 23 effective) — `test_coverage=1.0`
- **Build:** pass (`test_coverage=1.0` ⇒ build + tests succeeded; scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json); built `-Wall -Wextra`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `books.c:322` POST→`save_book(id=0)` INSERT of all 4 cols; test `create 201` (test_books.c:25) |
| R2 | GET /books lists all | ✓ implemented | `books.c:208` list_books SELECT all; test `list all` (test_books.c:69) |
| R3 | GET /books ?author= filter | ✓ implemented | `books.c:215` parses author, `WHERE author=?`; test `filter by author` (test_books.c:72) |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `books.c:330` get_book; `books.c:188` 404; tests `get by id`, `get missing 404` (test_books.c:29,32) |
| R5 | PUT /books/{id} updates | ✓ implemented | `books.c:331` PUT→`save_book(id>0)` UPDATE; test `update 200` (test_books.c:82) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books.c:332,288` delete_book→204; test `delete 204` (test_books.c:91) |
| R7 | Data stored in SQLite | ✓ implemented | `books.c:157` CREATE TABLE books; sqlite3 prepared stmts throughout |
| R8 | JSON responses + status codes | ✓ implemented | `server.c:32` Content-Type application/json; codes 201/200/204/400/404/405 |
| R9 | Validation: title + author required | ✓ implemented | `books.c:251` validate(); tests `missing title 400`, `blank author 400` (test_books.c:43,46) |
| R10 | GET /health | ✓ implemented | `books.c:316` returns `{"status":"ok"}`; test `health 200` (test_books.c:17) |
| R11 | README with setup/run | ✓ implemented | README.md — build/test/run + endpoint table + curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 test functions, 23 checks; `test_coverage=1.0` |

No partial or missing requirements. No skipped/disabled tests.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; DB row not
yet present). `test_coverage=1.0` ⇒ `make test` built and passed all checks;
`code_quality=1.0`.

```text
make            # cc -std=c11 -Wall -Wextra -O2 ... -lsqlite3  → books_server
make test       # builds test_books, runs it → "23/23 checks passed", exit 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 557 (books.c 336, server.c 98, books.h 13, test_books.c 110) |
| Files (src + tests) | 4 |
| Dependencies | 1 external lib (libsqlite3) |
| Tests total | 5 functions / 23 checks |
| Tests effective | 23 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from scores.json) |

Other stored scores: `maintainability=0.568`, `idiomatic=0.58`,
`token_efficiency=0.0241`, `defect_rate=1.0`.

## Findings

All 4 findings are non-defect (full list in `findings.jsonl`):

1. [low] `url_decode` percent-escape bounds check is convoluted (`books.c:198`)
2. [info] Transport/logic separation makes handlers directly testable (`books.h:12`)
3. [info] Hand-written JSON emitter escapes control chars and quotes (`books.c:28`)
4. [info] `?author=` filter is URL-decoded, percent and plus (`books.c:194`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                 # mechanical scores (test_coverage/code_quality/...)
cat ../../../REQUIREMENTS.json  # pinned 12-item checklist
grep -c 'CHECK(' tests/test_books.c
grep -cE '^static void test_' tests/test_books.c
# make test   # only if re-verifying build+tests; scores already recorded
```
