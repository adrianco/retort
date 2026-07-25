# Evaluation: language=c · model=claude-fable-5 · prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passed / 0 failed / 0 skipped (test_unit.c: ~40 CHECKs; test_api.sh: 36 checks — all effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build gate: `make` + `-lsqlite3`)
- **Lint:** pass — `code_quality=1.0` in scores.json (`-Wall -Wextra -std=c11`)
- **Architecture:** run-summary skill not available in this session; module map inlined below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean, fully-conforming run. A hand-written C11 REST service — no web framework — with
its own HTTP/1.1 server (`http.c`), JSON reader/writer (`json.c`), SQLite persistence
(`db.c`), and routing (`api.c`), split cleanly across headers. Mechanical scores from
`scores.json`: `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `idiomatic=0.76`,
`maintainability=0.57`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `api.c:179 handle_create` → `db.c:373 db_create_book` INSERT; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `api.c:195 handle_list` → `db.c:420 db_list_books_json` returns JSON array |
| R3 | GET /books supports ?author= filter | ✓ implemented | `api.c:197 http_query_param(...,"author")`; `db.c:422` `WHERE author = ?` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `api.c:204 handle_get`; `db.c:403 db_get_book` returns 1→404 mapping at `api.c:207` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.c:216 handle_update` → `db.c:452 db_update_book`; 0-changes→404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.c:236 handle_delete` → `db.c:466 db_delete_book`; returns 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `db.c:301 #include <sqlite3.h>`, `db.c:333 db_init` CREATE TABLE; `-lsqlite3` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `http.c:626 status_text` (200/201/204/400/404/405/500); `Content-Type: application/json` at `http.c:652` |
| R9 | Input validation: title and author required | ✓ implemented | `api.c:124`/`api.c:138` reject missing/null/blank title & author → 400; tested `test_unit.c:81` |
| R10 | GET /health health-check | ✓ implemented | `api.c:248` returns `{"status":"ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — build/run, env vars, API table, test instructions |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_unit.c` 6 test fns / ~40 CHECKs + `test_api.sh` 36 HTTP checks; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2):

```text
test_coverage = 1.0   ⇒  make + test_unit + test_api.sh all pass
code_quality  = 1.0   ⇒  -Wall -Wextra -std=c11 clean
defect_rate   = 1.0   ⇒  build + test succeeded
```

Test entry points:
```text
make test → ./test_unit  (JSON reader, book validation, query parsing, JSON output)
          → ./test_api.sh (live server: full CRUD, ?author filter, validation 400s, 404s, /health)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source .c/.h) | 1227 |
| Test lines (test_unit.c + test_api.sh) | 291 |
| Files (source + tests + build) | 12 (.c/.h/.sh/Makefile) |
| Dependencies | 1 (libsqlite3) |
| Tests total | ~40 unit CHECKs + 36 integration checks |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Architecture (run-summary unavailable)

- `main.c` — POSIX socket accept loop; per-connection read timeout; wires http → api → http.
- `http.c/.h` — minimal HTTP/1.1: request-line + Content-Length body parsing, response writer, `url_decode`, query-param extraction.
- `json.c/.h` — `strbuf` growable buffer + JSON string escaping; a top-level-key JSON reader with `\uXXXX` handling and nested value skipping.
- `db.c/.h` — SQLite schema + prepared-statement CRUD; `book` model; row↔JSON.
- `api.c/.h` — routing + validation; maps DB result codes to HTTP status.

## Findings

No defects. 2 info-level enhancements (full list in `findings.jsonl`):

1. [info] Hand-written JSON reader + HTTP/1.1 server, no framework — beyond-spec robustness.
2. [info] Distinguishes JSON missing/null/wrong-type for precise 400 validation messages.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-48-fable5-gaps/bookshop/runs/language=c_model=claude-fable-5_prompt=neutral/rep1
cat scores.json            # mechanical scores (not re-run)
make && make test          # optional: build + run unit + integration tests
grep -nE "t\.Skip|@skip|xfail" *.c *.sh   # confirms 0 real test skips
```
