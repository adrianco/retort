# Evaluation: erlang · hermes-local · Qwen3-Coder-Next-4bit · prompt=repair · stack=m80 · rep 2

> **SECOND OPINION.** This re-checks a prior evaluation that scored
> `requirement_coverage=0.3333` and flagged four defects. **All four are CONFIRMED**
> after reading the code — the first evaluator was right on every one. I re-score
> slightly *lower* (0.1667), because the wiring defect the first evaluator itself found
> also makes the list/filter routes (R2/R3) non-functional over HTTP, so they cannot be
> credited as implemented while the same wiring bug is cited against R8/R10.

## Summary

- **Factors:** language=erlang, agent=hermes-local, model=mlxlocal/Qwen3-Coder-Next-4bit, prompt=repair, stack=m80
- **Status:** failed (REST API non-functional: server not wired to router; core DB lookups broken; create path broken; storage not an embedded DB)
- **Requirements:** 2/12 implemented, 5 partial, 5 missing
- **Tests:** pass (test_coverage=1.0 from scores.json) — but the CRUD "integration" tests are `?assert(true)` stubs, so none of the four defects are exercised
- **Build:** pass — defect_rate=1.0, test_coverage=1.0 from scores.json (not re-run)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 10 items in `findings.jsonl` (2 critical, 2 high, 6 medium)

## Second-opinion verdict on the prior claims

| Prior claim | Verdict | Where I looked |
|----|----|----|
| R7 — in-memory ETS + ad-hoc file dump, not SQLite/embedded DB | **CONFIRMED** | `book_api_db.erl:17` `ets:new(books,...)`; term dump `book_api_db.erl:116-147`. No DETS/Mnesia/SQLite. |
| R4-R6 — ETS keypos bug, get/update/delete by id always not_found | **CONFIRMED** | `{keypos,2}` at `book_api_db.erl:17`; insert `{NextId,NewBook}` at `:69` → key is the map; `ets:lookup(books,Id)` at `:42,:81,:103` never matches an integer. |
| R1 — POST create binary-vs-atom key mismatch always 400 | **CONFIRMED** | handler `parse_json` builds binary keys `book_api_handler.erl:210-244`; `create_book/1` matches atom keys `book_api_db.erl:50` → `{error,invalid_data}`. The correct `book:parse_json` (`book.erl:64`) is never called by the handler. |
| R8-R10 — HTTP server not wired to router | **CONFIRMED** | httpd `modules=[book_api_http]` `book_api_http.erl:12-19`; no `do/1` exported anywhere (grep); `book_api_handler` referenced by nothing but its own module line (grep). Router is dead code. |

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✗ missing | binary/atom key mismatch → always 400 (`book_api_handler.erl:210-244` vs `book_api_db.erl:50`); also unreachable |
| R2 | GET /books list all | ~ partial | `get_all_books` (`book_api_db.erl:29`) + `handle_books_list` (`book_api_handler.erl:36`) correct, but unreachable (no wiring) |
| R3 | ?author= filter | ~ partial | `books_filter_by_author` (`book_api_handler.erl:144`) present, unreachable |
| R4 | GET /books/{id} | ✗ missing | keypos bug → always not_found (`book_api_db.erl:17,42,69`); unreachable |
| R5 | PUT /books/{id} | ✗ missing | keypos bug → always not_found (`book_api_db.erl:81`); unreachable |
| R6 | DELETE /books/{id} | ✗ missing | keypos bug → always not_found (`book_api_db.erl:103`); unreachable |
| R7 | SQLite/embedded DB | ✗ missing | in-memory ETS + ad-hoc file dump (`book_api_db.erl:17,116-147`) |
| R8 | JSON + status codes | ~ partial | `send_response`/`json_encode` correct (`book_api_handler.erl:120-191`) but never emitted (no wiring) |
| R9 | Validation title/author | ~ partial | `book:validate/1` (`book.erl:4-53`) exists but handler never calls it; create path broken/unreachable |
| R10 | GET /health | ~ partial | route present (`book_api_handler.erl:19`), unreachable |
| R11 | README.md | ✓ implemented | `README.md` (2854 bytes) with Features/setup/run |
| R12 | ≥3 tests, coverage>0 | ✓ implemented | test_coverage=1.0; multiple eunit suites (though CRUD tests are stubs) |

**requirement_coverage = 2/12 = 0.1667** (implemented; partial and missing both count as not-implemented).

## Build & Test

Not re-run — stored scores used per skill step 2:

```text
scores.json: {"code_quality":1.0,"token_efficiency":0.5,"test_coverage":1.0,
              "defect_rate":1.0,"maintainability":0.674,"idiomatic":0.32}
```

`test_coverage=1.0` means the eunit suites compile and pass, but they validate `book.erl`
helpers and DB *error* paths only; `handler_health_endpoint/0` and `handler_books_crud/0`
(`book_api_test.erl:117-125`) are `?assert(true)` stubs. The green tests do not exercise a
single insert→lookup round-trip, so they are blind to all four confirmed defects.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test .erl) | 899 |
| Files (excl. _build/ebin) | 24 |
| Tests total | ~15 eunit assertions across 2 suites |
| Tests effective (non-stub) | ~13 (2 CRUD/health tests are `?assert(true)`) |
| Storage | in-memory ETS + file term dump |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] R8-R10-wiring — httpd started with `modules=[book_api_http]` but no `do/1`; router `book_api_handler` never invoked → no route reachable.
2. [critical] R4-R6-keypos — `{keypos,2}` vs `{NextId,NewBook}` inserts → get/update/delete by id always `not_found`.
3. [high] R1-keymismatch — handler emits binary keys, `create_book/1` matches atom keys → all POST /books return 400.
4. [high] R7 — storage is in-memory ETS + ad-hoc file dump, not an embedded DB.
5. [high] test-hollow-crud — CRUD "integration" tests are `?assert(true)` stubs; `test_coverage=1.0` is misleading.

## Reproduce

```bash
cd experiments/adrianco/experiment-41-repair-80b-fullctx/bookshop/runs/agent=hermes-local_language=erlang_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=repair_stack=m80/rep2
cat scores.json                                   # stored build/test/lint scores
grep -rn "book_api_handler" src/                  # referenced only by its own module line
grep -rn "^do(\|-export.*do/1" src/               # no httpd do/1 callback anywhere
grep -n "keypos\|ets:insert\|ets:lookup" src/book_api_db.erl
```
