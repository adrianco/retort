# Evaluation: agent=codex effort=low language=erlang model=gpt-6-luna prompt=neutral · rep 2

## Summary (SECOND OPINION — re-check of a prior 0.3333 evaluation)

- **Factors:** language=erlang, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok (built + tests pass) but HTTP service does not serve — two confirmed fatal runtime bugs
- **Requirements:** 4/12 implemented, 6 partial, 2 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — test_coverage=1.0 from scores.json
- **Build:** pass — code compiles (debug_info); defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json
- **Findings:** 3 items in `findings.jsonl` (1 critical, 2 high)

### Second-opinion verdict on the prior claims

Both requirements the first evaluator flagged as NOT met are **CONFIRMED real bugs**. First
evaluations usually miss *existing* implementations; here the prior claims were accusations of
*defects*, and both check out against the source and the pinned cowboy 2.12.0 dependency.

- **bug-init-contract — CONFIRMED.** `src/books_http_handler.erl:5,12` — every `init/2` clause
  tail-calls `reply/3` (line 23) or `book_route/3`, all of which return `cowboy_req:reply/4`'s
  value, a bare `Req` map. `cowboy_handler:execute/2` (cowboy 2.12.0, `rebar.lock`) matches only
  `{ok,Req,State}` / `{Mod,Req,State}` / `{Mod,Req,State,Opts}`; a bare map raises a `try_clause`
  and the request process is terminated. The HTTP layer is untested, so this passed
  `test_coverage=1.0` yet no route serves cleanly.
- **bug-qs-val — CONFIRMED.** `src/books_http_handler.erl:10` calls `cowboy_req:qs_val/2`;
  `rebar.config:2` / `rebar.lock` pin cowboy `2.12.0`, where `qs_val` was removed in Cowboy 2.0
  (replaced by `parse_qs/1` / `match_qs/2`). GET /books (R2, R3) raises `undef` before any reply.

The re-scored `requirement_coverage` is **0.3333 (4/12)** — unchanged from the prior evaluation,
and now independently verified requirement-by-requirement below.

## Requirements (pinned REQUIREMENTS.json, 12 items)

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `books_http_handler.erl:7-9` + `books_db:create` present, but init/2 contract bug crashes the request process |
| R2 | GET /books lists all | ✗ missing | `books_http_handler.erl:10` — `qs_val/2` undef in cowboy 2.x; crashes before reply |
| R3 | GET /books ?author= filter | ✗ missing | same `qs_val/2` undef — the filter mechanism itself never runs |
| R4 | GET /books/{id} | ~ partial | `book_route(<<"GET">>...)` + `books_db:get`, but init/2 contract bug |
| R5 | PUT /books/{id} | ~ partial | `book_route(<<"PUT">>...)` + `books_db:update`, but init/2 contract bug |
| R6 | DELETE /books/{id} | ~ partial | `book_route(<<"DELETE">>...)` + `books_db:delete`, but init/2 contract bug |
| R7 | Stored in SQLite / embedded DB | ✓ implemented | `books_db.erl` shells to `sqlite3 -json`; CREATE TABLE + CRUD SQL |
| R8 | JSON responses + status codes | ~ partial | `reply/3` sets JSON content-type + jsx:encode; codes 200/201/400/404/204/405/500 wired, but delivery broken by init/2 |
| R9 | Validation: title+author required | ✓ implemented | `decode_book/1:19` checks `nonempty(T) andalso nonempty(A)` → 400; tested (`validation_test`, `decode_book_test`) |
| R10 | GET /health | ~ partial | `init(Req,health):5` replies 200 ok, but init/2 contract bug |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, run, endpoints, tests |
| R12 | >= 3 tests that run | ✓ implemented | `test/books_api_tests.erl` — 3 tests, 0 skips, test_coverage=1.0 |

Implemented = R7, R9, R11, R12 → **4/12 = 0.3333**. Partials (logic present, HTTP layer broken by
init/2) and missing (qs_val) are not counted toward coverage.

## Build & Test

Scores read from `scores.json` (not re-run, per skill): `test_coverage=1.0`, `defect_rate=1.0`,
`code_quality=1.0`, `maintainability=0.74`, `idiomatic=0.05`, `token_efficiency=0.0`. The tests
compile and pass, but they cover only `nonempty/1`, `decode_book/1` and `books_db` CRUD — never the
Cowboy request path, which is where both fatal bugs live.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 120 |
| Files | 6 |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

1. [critical] bug-init-contract — init/2 returns a bare Req; every route crashes its request process (`books_http_handler.erl:5,12`)
2. [high] bug-qs-val — GET /books calls cowboy_req:qs_val/2, removed in Cowboy 2.x (`books_http_handler.erl:10`)
3. [high] test-http-gap — no test exercises the HTTP layer, so both bugs pass unflagged (`books_api_tests.erl:4-17`)

## Reproduce

```bash
cd <run_dir>
grep -n "init(Req" src/books_http_handler.erl    # init/2 clauses all return reply(...)
grep -n "qs_val" src/books_http_handler.erl       # line 10
grep -i cowboy rebar.lock                          # 2.12.0
cat scores.json                                    # test_coverage=1.0 (HTTP untested)
```
