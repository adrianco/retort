# Evaluation: language=c · model=gpt-5.6-terra · agent=codex · rep 1

## Summary

- **Factors:** language=c, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective unit tests; integration script present but not run in sandbox)
- **Build:** pass — `make` (cc -std=c11 -Wall -Wextra -Werror -O2, links -lsqlite3); test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=0.9556 from scores.json; compiles clean under -Werror
- **Architecture:** single-file C HTTP server (`book_api.c`, 161 lines) over raw BSD sockets with SQLite persistence; summary skill unavailable
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_api.c:99-109` INSERT + 201 response |
| R2 | GET /books lists all books | ✓ implemented | `book_api.c:110-116` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `book_api.c:145-149` url_decode + `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `book_api.c:117-122` `WHERE id=?`, 404 if absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `book_api.c:123-130` UPDATE, 404 if no change |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `book_api.c:131-134` DELETE, 200/404 |
| R7 | Data stored in SQLite | ✓ implemented | `book_api.c:155` sqlite3_open + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `book_api.c:70-76` reply() sets 200/201/400/404/405 + Content-Type json |
| R9 | Validation: title & author required | ✓ implemented | `book_api.c:87-95` valid_book returns 0 → 400 (line 100/124) |
| R10 | GET /health endpoint | ✓ implemented | `book_api.c:143` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-41` build, run, endpoints, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_book_api.c` 3 unit tests + `test_api.sh` integration; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill):

```text
make            # cc -std=c11 -Wall -Wextra -Werror -O2 -o book_api book_api.c -lsqlite3
test_coverage=1.0  → build + tests passed
defect_rate=1.0
```

```text
make test       # compiles test_book_api.c (which #includes book_api.c with main renamed)
./test_book_api
All unit tests passed.
```

Agent log (`_agent_stdout.log`) confirms the sandbox blocks loopback `listen()`, so the
default `test` target was switched to portable unit tests over the pure JSON/validation
helpers; `make integration-test` (test_api.sh) remains for permissive environments.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 161 (book_api.c) + 40 (test_book_api.c) + 28 (test_api.sh) |
| Files | 6 (book_api.c, test_book_api.c, test_api.sh, Makefile, README.md, book_api binary) |
| Dependencies | 1 (libsqlite3) |
| Tests total | 3 unit (+ integration script) |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] List responses truncate into a fixed 8192-byte buffer — large collections yield malformed JSON (`book_api.c:113-115,148`)
2. [info] Dead `filter` variable in handle_books GET branch (`book_api.c:111`)
3. [info] Default `make test` runs only unit tests; integration script not exercised in sandbox (reasonable adaptation; R12 still met)

No critical or high findings. Requirement coverage 12/12.

## Reproduce

```bash
cd "runs/agent=codex_effort=default_language=c_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (test_coverage=1.0)
make                                   # build (needs libsqlite3)
make test                             # 3 portable unit tests
make integration-test                 # full HTTP suite (needs loopback listen)
```
