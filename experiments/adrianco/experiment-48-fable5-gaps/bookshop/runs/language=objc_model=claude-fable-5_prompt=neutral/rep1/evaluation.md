# Evaluation: language=objc_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 34 assertions across 7 test functions passed / 0 failed / 0 skipped (34 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (build + all tests passed)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** run-summary skill unavailable in this session — see module notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

A complete, idiomatic Objective-C REST service. A hand-rolled BSD-socket HTTP server
(`HTTPServer.m`) dispatches to a router (`BookAPI.m`) over a SQLite-backed store
(`BookStore.m`) with a serial dispatch queue for thread safety. Every pinned
requirement is satisfied with test evidence.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookAPI.m:128` POST → `BookStore.m:114 createBook`; test `tests.m:65 TestCreateAndGet` (201) |
| R2 | GET /books lists all | ✓ implemented | `BookAPI.m:123` GET → `BookStore.m:134 booksWithAuthor:nil`; test `tests.m:116` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookAPI.m:124` reads `query[@"author"]`; SQL `WHERE author = ?` `BookStore.m:138`; test `tests.m:129` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `BookAPI.m:140`; 404 at `:142`; test `tests.m:178` non-existent → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookAPI.m:145` → `BookStore.m:160 updateBookWithId`; test `tests.m:140 TestUpdate` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookAPI.m:153` → `BookStore.m:180 deleteBookWithId`; 204; test `tests.m:163` |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore.m:15 sqlite3_open`, schema `:26`, prepared statements throughout |
| R8 | JSON responses + status codes | ✓ implemented | `HTTPResponse responseWithStatus:JSONObject:` `HTTPServer.m:35`; 201/200/204/400/404/405 all used |
| R9 | Validation: title+author required | ✓ implemented | `ValidateBookFields` `BookAPI.m:24` rejects empty/whitespace title & author (400); test `tests.m:82 TestValidation` |
| R10 | GET /health | ✓ implemented | `BookAPI.m:101` returns `{"status":"ok"}`; test `tests.m:58 TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` present (3.2KB) with build/run/endpoint docs |
| R12 | >= 3 tests | ✓ implemented | 7 test functions / 34 assertions, `tests.m`; test_coverage=1.0 |

Beyond spec (not deductions): trailing-slash normalization (`BookAPI.m:97`), 405
Method Not Allowed handling, strict numeric-id parsing (`ParseBookId` `:83`),
1 MB request-size cap (`HTTPServer.m:7`), and `@try/@catch` → 500 guard around the
handler (`HTTPServer.m:240`).

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 1.0   → build succeeded + all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
```

```text
booktests (tests.m): 7 test functions, 34 CHECK assertions, 0 skipped
Exercises health, create+get, validation (missing title / blank author /
non-numeric year / malformed JSON), list + author filter, update (incl. 400 & 404),
delete (incl. double-delete 404), and 405 method-not-allowed paths.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source .h/.m only) | 992 |
| Files (excl. binaries, agent log) | 16 |
| Dependencies | 0 external (Foundation + libsqlite3 system libs) |
| Tests total | 34 assertions / 7 functions |
| Tests effective | 34 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] PUT replaces the whole resource (title+author required on update) — standard PUT semantics
2. [info] SQLite persistence with a serial dispatch queue for thread-safe access
3. [info] Tests are real HTTP integration tests over an ephemeral port

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-48-fable5-gaps/bookshop/runs/language=objc_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                      # stored mechanical scores (build/test/lint)
make                                 # builds bookserver + booktests
./booktests                          # runs the integration suite (prints "ALL TESTS PASSED")
```
