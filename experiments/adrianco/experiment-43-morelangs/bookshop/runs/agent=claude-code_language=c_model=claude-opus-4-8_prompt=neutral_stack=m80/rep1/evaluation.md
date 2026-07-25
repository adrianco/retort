# Evaluation: agent=claude-code language=c model=claude-opus-4-8 prompt=neutral stack=m80 · rep 1

## Summary

- **Factors:** language=c, model=claude-opus-4-8, agent=claude-code, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 test functions / all passing / 0 skipped (from `test_coverage=1.0`)
- **Build:** pass — `test_coverage=1.0`, `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** hand-rolled HTTP/1.1 server (`main.c`) + testable router (`api.c`) + SQLite persistence (`db.c`) + minimal JSON parser/builder (`json.c`); `summary/` not generated (run-summary skill unavailable)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `api.c:147 handle_create` → `db.c:65 db_create_book`, returns 201 |
| R2 | GET /books lists books | ✓ implemented | `api.c:169 handle_list` → `db.c:118 db_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `api.c:170 query_get(query,"author")`, `db.c:120` WHERE author=? |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `api.c:189 handle_get`; 404 at `api.c:195` when rc==0 |
| R5 | PUT /books/{id} updates | ✓ implemented | `api.c:201 handle_update` → `db.c:153 db_update_book`; 404 on missing |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `api.c:225 handle_delete` → `db.c:177 db_delete_book`; 404 on missing |
| R7 | Data stored in SQLite | ✓ implemented | `db.c:21-42` sqlite3_open + CREATE TABLE books; prepared statements throughout |
| R8 | JSON responses + status codes | ✓ implemented | `main.c:76 send_response` Content-Type application/json; codes 200/201/400/404/405/500 |
| R9 | Validation: title+author required | ✓ implemented | `api.c:128-135 extract_book_fields` → 400 "title/author is required" |
| R10 | GET /health | ✓ implemented | `api.c:244` returns `{"status":"ok"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — layout, prerequisites, build/run/test instructions |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test.c` — 7 test functions, all passing (`test_coverage=1.0`) |

**Prompt factor (`neutral`):** `prompts/neutral.md` prescribes no methodology and only asks for tests that demonstrate the requirements — satisfied by R12 (7 hermetic integration/unit tests). No additional checkable `P*` requirements.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
code_quality:     1.0
test_coverage:    1.0   (build + all tests passed)
defect_rate:      1.0   (build+test succeeded)
maintainability:  0.484
idiomatic:        0.8
token_efficiency: 0.038
```

Test entry point: `test.c:244 main()` runs 7 suites; `make test` builds `test_runner` and executes it (`Makefile:15-19`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .c/.h) | 1415 |
| Source LOC (excl. test.c) | ~1160 |
| Files | 18 (8 source, plus README/Makefile/build artifacts/logs) |
| Dependencies | 1 (SQLite; no external HTTP/JSON libs) |
| Test functions | 7 |
| Tests skipped | 0 |
| Skip ratio | 0% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] Unbounded request body buffering — `read_request` grows without a size cap (`api.c:36-70`)
2. [low] malloc/realloc return values unchecked in request reader (`api.c:31,39`)
3. [info] Test suite exceeds the 3-test minimum — 7 functions, dozens of assertions

None are conformance failures; all requirements are implemented and verified.

## Reproduce

```bash
cd experiments/adrianco/experiment-43-morelangs/bookshop/runs/agent=claude-code_language=c_model=claude-opus-4-8_prompt=neutral_stack=m80/rep1
cat scores.json                     # mechanical scores (build/test/lint)
make test                           # build + run the 7 test suites
grep -cE "^static void test_" test.c   # test function count
wc -l *.c *.h                       # LOC
```
