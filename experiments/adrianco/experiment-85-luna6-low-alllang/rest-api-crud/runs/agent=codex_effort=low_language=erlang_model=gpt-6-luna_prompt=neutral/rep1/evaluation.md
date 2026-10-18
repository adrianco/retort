# Evaluation: agent=codex_effort=low_language=erlang_model=gpt-6-luna_prompt=neutral · rep 1

*Second-opinion re-check of a prior evaluation (2026-10-18). The prior evaluator's one MISSING claim — `http-routing` — is **confirmed**, now by execution rather than only by reading the code.*

## Summary

- **Factors:** language=erlang, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** failed (routing defect: every HTTP request returns 404)
- **Requirements:** 3/12 implemented, 0 partial, 9 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 eunit tests; test_coverage=1.0 from scores.json (3 effective, 0 skipped)
- **Build:** pass (derived: test_coverage=1.0, defect_rate=1.0)
- **Lint:** code_quality=1.0
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (1 critical, 1 high, 1 medium, 1 low)

## Re-check of the prior claim

**http-routing: CONFIRMED.** The burden of proof was on "missing", so I tried to falsify it:

- `src/books_api_app.erl:6` defines the routes `"/health"`, `"/books"`, `"/books/:id"`, with no `[...]` path_info segment.
- In Cowboy 2.12.0 (the version pinned in `rebar.lock`), `cowboy_router.erl:385-386` is `list_match([], [], Binds) -> {true, Binds, undefined};`, and `execute/2` (line 172) stores that value as `path_info`.
- **Executed check:** I compiled that cowboy_router and cow_uri into a temp dir and called `cowboy_router:match/3` on this run's exact dispatch:
  ```text
  /health  -> {ok,h,[],#{},undefined,undefined}
  /books   -> {ok,h,[],#{},undefined,undefined}
  /books/1 -> {ok,h,[],#{id => <<"1">>},undefined,undefined}
  ```
  The last element is PathInfo, and it is `undefined` for all three routes.
- `src/books_api_handler.erl:7` passes `cowboy_req:path_info(Req)`, which is `undefined`, into `route/3`. Every clause at lines 13-34 pattern-matches a binary-token list such as `[<<"books">>]`, so nothing matches and the catch-all at line 35 returns `404 not_found`.
- I searched for another dispatch path and found none: no use of `cowboy_req:path/1` or `cowboy_req:binding/2`, and no per-route State.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates | ✗ missing | store `create/1` works (`books_api_store.erl:18`), but the HTTP route is unreachable (`books_api_handler.erl:17` never matched → :35 404) |
| R2 | GET /books lists | ✗ missing | `books_api_handler.erl:14` unreachable |
| R3 | ?author= filter | ✗ missing | store filter exists (`books_api_store.erl:22`), but the route at handler:14 is unreachable |
| R4 | GET /books/{id} | ✗ missing | handler:23 unreachable |
| R5 | PUT /books/{id} | ✗ missing | handler:24 unreachable |
| R6 | DELETE /books/{id} | ✗ missing | handler:30 unreachable |
| R7 | SQLite storage | ✓ implemented | `books_api_store.erl:16,38` uses a sqlite3 file DB; exercised by `store_crud_test` |
| R8 | JSON + correct status codes | ✗ missing | every request gets a 404 JSON response, so the 201/200/400 codes are never produced |
| R9 | title/author validation (400) | ✗ missing | `validate/1` (handler:42) is correct and unit-tested, but the 400 response path is unreachable over HTTP |
| R10 | GET /health | ✗ missing | handler:13 unreachable; GET /health returns 404 |
| R11 | README | ✓ implemented | `README.md` covers setup, run, endpoints and tests |
| R12 | ≥3 tests | ✓ implemented | `test/books_api_tests.erl`: validation_test, store_crud_test, unknown_book_test; test_coverage=1.0 |

requirement_coverage = 3/12 = **0.25** (unchanged from the first evaluation)

## Build & Test

Not re-run, per the skill. scores.json: `test_coverage=1.0, defect_rate=1.0, code_quality=1.0, maintainability=0.795, idiomatic=0.08`. The tests pass only because none of them touch the HTTP layer.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 125 (3 modules) |
| Files | 4 src + 1 test |
| Dependencies | 2 direct (cowboy 2.12.0, jsx 3.1.0) |
| Tests total / effective | 3 / 3 |
| Skip ratio | 0% |

## Findings

1. [critical] Every HTTP request returns 404, because the handler dispatches on `path_info`, which is undefined for these routes
2. [high] No test exercises the HTTP layer
3. [medium] SQL is built by string concatenation and run through the sqlite3 CLI
4. [low] A partial request body (`{more, ...}`) is decoded as if complete

## Reproduce

```bash
L=../rep2/_build/default/lib; T=$(mktemp -d); cd $T
erlc +export_all -I $L/cowlib/include -o . $L/cowboy/src/cowboy_router.erl $L/cowlib/src/cow_uri.erl
erl -noshell -pa . -eval 'D=cowboy_router:compile([{'_',[{"/health",h,[]},{"/books",h,[]},{"/books/:id",h,[]}]}]), [io:format("~s -> ~p~n",[P,cowboy_router:match(D,<<"localhost">>,P)]) || P <- [<<"/health">>,<<"/books">>,<<"/books/1">>]], halt().'
```
