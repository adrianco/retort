# Evaluation: c · hermes-local · Qwen3-Coder-Next-4bit · prompt=neutral · stack=m80 · rep 1

## Summary

- **Factors:** language=c, agent=hermes-local, model=mlxlocal/Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80 (repair task)
- **Status:** ok — repair passed; build + all tests run and pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 integration tests, 0 skipped (16 effective) — all pass (`test_coverage=1.0` in `scores.json`)
- **Build:** pass — `test_coverage=1.0` ⇒ `gcc` build succeeded (binary `book-api` rebuilt at score time)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session — see Build & Test / source notes below
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 3 info)

This is a **repair task**: a prior attempt failed independent evaluation (FEEDBACK.md: "build/tests did not fully pass"). The current archive builds cleanly and every requirement is met. Notably, the repair agent hit its tool-call iteration limit and only *summarized* proposed fixes without editing files (`_agent_stdout.log:34`, `.hermes_usage.json` `completed:false`); the run passes because the prior code was already functionally correct — the earlier failure was environmental (the exp-43 test-server port leak fixed in the harness), not a code defect. See finding F5.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `http.c:301 create_book` → `db.c:209 db_create_book`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `http.c:143 get_books` → `db.c:81 db_get_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `http.c:154` parses `author=`, `db.c:138 db_get_books_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `http.c:218 get_book`; 404 at `http.c:221` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `http.c:350 update_book` → `db.c:267 db_update_book`; 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `http.c:403 delete_book` → `db.c:324`; 204 success / 404 absent |
| R7 | Data stored in SQLite | ✓ implemented | `db.c:8 db_init` opens sqlite3, `CREATE TABLE books`, all CRUD via sqlite3 |
| R8 | JSON responses + correct status codes | ✓ implemented | `http.c:48 http_build_response` (200/201/204/400/404/500), JSON bodies throughout |
| R9 | Validation: title & author required | ✓ implemented | `http.c:317` rejects empty title/author with 400; tests 3–6 assert 400 |
| R10 | GET /health | ✓ implemented | `http.c:133 health_check` returns `{"status":"healthy",...}` 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, options, API examples, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | `run_tests.sh` — 16 curl-based integration tests, 0 skipped |

## Build & Test

Scores read from `scores.json` (skill forbids re-running the toolchain):

```text
code_quality      = 1.0
test_coverage     = 1.0   # build succeeded + all tests passed (test gate)
defect_rate       = 1.0
maintainability   = 0.4286
idiomatic         = 0.78
token_efficiency  = 0.0053   # 3.72M total tokens / 90 api calls — very low efficiency
```

Test harness (`run_tests.sh`) starts `./book-api` on port 8765 and asserts HTTP codes for
16 cases: health check, create (valid → 201), 4× validation (missing/empty title/author → 400),
get-by-id (200), get-missing (404), update (200), list (200), author filter (200),
delete (204), delete-missing (404), and three further creates + list. No skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (c/h, source only) | 1114 (main 241 + http 450 + db 350 + headers 73) |
| Dead code (debug_db.c, unbuilt) | 148 |
| Source files (excl. binary/db) | 18 (incl. logs, scripts) |
| Dependencies | libcurl, libsqlite3, pthread |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] F1 — GET /books serializes the whole list into a fixed 4096-byte buffer; large collections truncate to invalid JSON (`http.c:174`). Latent — never triggers at the ≤3-book test scale.
2. [low] F2 — SQL built by string formatting with manual quote-escaping instead of bind parameters (`db.c:155,252,310,328`); correct escaping, so no demonstrable injection.
3. [info] F3 — `debug_db.c` (148 LOC) is dead code, not in `Makefile` SRCS.
4. [info] F4 — `create_book` reuses the `isbn` buffer to parse `year` (`http.c:313-315`); works but fragile.
5. [info] F5 — Repair agent stopped at the tool-call iteration limit without editing files; run passes because prior code already worked (environmental earlier failure).

## Reproduce

```bash
cd experiments/adrianco/experiment-43-morelangs/bookshop/runs/agent=hermes-local_language=c_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat scores.json                        # stored build/test/lint scores (do not re-run)
grep -c '^run_test ' run_tests.sh      # 16 tests, 0 skips
wc -l main.c http.c db.c *.h           # source LOC
# build/test are NOT re-run — test_coverage=1.0 already proves gcc build + all tests pass
```
