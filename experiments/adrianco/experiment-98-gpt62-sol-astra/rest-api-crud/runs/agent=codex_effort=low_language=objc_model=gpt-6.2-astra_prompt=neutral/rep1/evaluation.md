# Evaluation: rest-api-crud · agent=codex effort=low language=objc model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `make` (clang, Foundation + libsqlite3); not re-run (test_coverage=1.0 ⇒ build succeeded)
- **Lint:** n/a — no lint scorer for objc; `code_quality=0.78` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Books.m:84-86` INSERT ... RETURNING *, status 201; `test_books.py:28` |
| R2 | GET /books lists all books | ✓ implemented | `Books.m:65` SELECT * ORDER BY id; `test_books.py:42` |
| R3 | GET /books ?author= filter | ✓ implemented | `Books.m:62-64` WHERE author=?; `test_books.py:43-44` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `Books.m:67` single=YES; 404 via `Books.m:42`; `test_books.py:36-37` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Books.m:88` UPDATE ... RETURNING *; `test_books.py:32-34` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Books.m:68-69` DELETE ... RETURNING id; `test_books.py:35` |
| R7 | Data stored in SQLite | ✓ implemented | `Books.m:137-139` sqlite3_open + CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `Books.m:127-132` JSON body + status phrases 200/201/400/404/405/413/500 |
| R9 | Input validation: title & author required | ✓ implemented | `Books.m:74-78` reject blank title/author (400); `test_books.py:46-50` |
| R10 | GET /health health-check | ✓ implemented | `Books.m:50` returns {"status":"ok"}; `test_books.py:24-25` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build/run, env vars, route table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_books.py` — 4 test methods; test_coverage=1.0 |

## Build & Test

Build and tests were **not re-run** — `scores.json` already records the scorer's results:

```text
scores.json: {"code_quality": 0.778, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.667, "idiomatic": 0.4, "token_efficiency": 0.025}
```

`test_coverage=1.0` ⇒ `make test` built `books` (clang, -fobjc-arc, Foundation + libsqlite3)
and all 4 `unittest` tests passed. `defect_rate=1.0` corroborates build+test success.
Tests drive the executable via its `--stdio` single-request mode against a per-test temp
SQLite DB (`test_books.py:18`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 211 (Books.m 161, test_books.py 50) |
| Files | 12 (incl. compiled `books`, logs, caches) |
| Dependencies | 0 third-party (Foundation + system libsqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] Author filter is exact and case-sensitive — spec only asks for a filter (satisfied)
2. [info] Hardened HTTP parsing beyond spec (Transfer-Encoding rejected, 1 MiB body cap, socket timeouts)

No critical/high/medium/low findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=objc_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build+test not re-run)
grep -cE "def test_" test_books.py
# optional live rebuild/test (NOT needed — scores.json is authoritative):
# make test
```
