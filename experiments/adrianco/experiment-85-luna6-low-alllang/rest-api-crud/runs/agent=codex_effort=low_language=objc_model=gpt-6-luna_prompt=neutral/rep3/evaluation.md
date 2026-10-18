# Evaluation: agent=codex_effort=low_language=objc_model=gpt-6-luna_prompt=neutral · rep 3

## Summary

- **Factors:** language=objc, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Prompt (neutral):** P1 "include tests that demonstrate the implementation meets the requirements" — implemented (logic-level; HTTP socket path untested, see findings)
- **Tests:** 8 checks passed / 0 failed / 0 skipped (8 effective), in 1 test function — test_coverage=1.0 from `scores.json`
- **Build:** pass — defect_rate=1.0 from `scores.json` (not re-run)
- **Lint:** pass — code_quality=1.0 from `scores.json`
- **Other stored scores:** maintainability=0.565, idiomatic=0.35, token_efficiency=0.0071
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 4 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `BookServer.m:122` → `createBook:` (:65); Tests.m:11 expects 201 |
| R2 | GET /books lists all | ✓ implemented | `BookServer.m:121`, `allBooksByAuthor:` (:40) |
| R3 | ?author= filter | ✓ implemented | `BookServer.m:41` `WHERE author LIKE ?`; Tests.m:12 (exact-match semantics, README says substring — low finding) |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `BookServer.m:124`; Tests.m:13, :16 |
| R5 | PUT /books/{id} | ✓ implemented | `BookServer.m:125` → `updateBook:` (:74); Tests.m:14 |
| R6 | DELETE /books/{id} | ✓ implemented | `BookServer.m:126` (204 / 404); Tests.m:15 |
| R7 | SQLite storage | ✓ implemented | `BookServer.m:19-23` sqlite3_open + CREATE TABLE, prepared statements throughout |
| R8 | JSON + appropriate status codes | ✓ implemented | `sendStatus:` `BookServer.m:109-112` (Content-Type application/json; 200/201/204/400/404/405/500) |
| R9 | title & author required | ✓ implemented | `validBookFields:` `BookServer.m:89` (non-blank strings); Tests.m:10 expects 400 |
| R10 | GET /health | ✓ implemented | `BookServer.m:119`; Tests.m:9 |
| R11 | README with setup/run | ✓ implemented | `README.md:10-17`, `:36-40` |
| R12 | ≥3 tests | ✓ implemented | Tests.m: 8 distinct checks, all pass (test_coverage=1.0) — single function, see info finding |

**Note on test scope:** the tests drive `responseForMethod:target:body:`, a duplicate of the live `serveClient:` routing; the TCP server is never exercised. The agent says the sandbox blocked local socket binding (`_agent_stdout.log`, final message) — so this gap is partly harness-induced, not purely a model choice.

## Build & Test

Not re-run (stored scores exist). Agent's own final verification from `_agent_stdout.log`:

```text
make clean && make && make test
clang -fobjc-arc -Wall -Wextra -Wno-unused-parameter -framework Foundation main.m BookServer.m -o book-service -lsqlite3
clang -fobjc-arc -Wall -Wextra -Wno-unused-parameter -framework Foundation Tests.m BookServer.m -o book-tests -lsqlite3
./book-tests
All integration logic checks passed
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: .m/.h) | 202 (BookServer.m 144, main.m 20, Tests.m 19, BookServer.h 19) |
| Files (source + build + docs) | 6 (+ compiled `book-service` binary) |
| Dependencies | 2 system (Foundation, libsqlite3) |
| Tests total | 8 checks |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Routing duplicated in `serveClient:` / `responseForMethod:`; tests cover only the copy, and the two already diverge on non-object bodies
2. [medium] Serial accept loop + blocking recv with no timeout — one idle client stalls the server
3. [low] README says substring author filter; code is case-insensitive exact LIKE with unescaped wildcards
4. [low] `year` not type-validated — `"abc"` stored as 0
5. [low] `/books/1abc` resolves to book 1 (lenient integerValue)

Code is dense (many statements per line, `BookServer.m:106` is one ~600-char line), consistent with idiomatic=0.35 and maintainability=0.56.

## Reproduce

```bash
cd "<run_dir>"
cat scores.json
cat ../../../REQUIREMENTS.json
make test   # optional; scores already stored
```
