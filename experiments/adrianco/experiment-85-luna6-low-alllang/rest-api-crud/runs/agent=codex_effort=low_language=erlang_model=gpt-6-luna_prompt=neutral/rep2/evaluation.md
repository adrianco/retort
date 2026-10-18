# Evaluation: agent=codex_effort=low_language=erlang_model=gpt-6-luna_prompt=neutral · rep 2

*Second-opinion re-check of a prior evaluation that scored 0.5. Both claims of missing requirements were re-verified, by reading the code and by running a live HTTP probe on a temporary copy. Both are CONFIRMED.*

## Summary

- **Factors:** language=erlang, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral (repair attempt — see FEEDBACK.md)
- **Status:** failed (conformance) — builds and the unit tests pass, but POST, PUT and GET /books crash for every real HTTP request
- **Requirements:** 6/12 implemented, 2 partial (R8, R9), 4 missing (R1, R2, R3, R5)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — test_coverage=1.0 from scores.json
- **Build:** pass (defect_rate=1.0, scores.json)
- **Lint:** code_quality=1.0 (scores.json)
- **Architecture:** summary skill not run. The app is small: app/sup, a gen_server `books_db` that shells out to the `sqlite3 -json` CLI, and a single cowboy handler.
- **Findings:** 4 in `findings.jsonl` (2 critical, 1 high, 1 medium)

## Re-check of the prior claims

| Claim | Verdict | Evidence |
|---|---|---|
| POST/PUT read_body matched as a 2-tuple | **CONFIRMED** | `src/books_http_handler.erl:9`, `:16` `{Body,R}=cowboy_req:read_body(Req)`, but Cowboy's `read_body` returns `{ok,Body,Req}` (cowboy_req.erl:512). Live: POST valid → 500; POST missing author → 500 (not 400); PUT → 500. Log shows `badmatch,{ok,<<"{\"title\":\"Dune\"...`. |
| GET /books parse_qs shim returns the raw binary | **CONFIRMED** | `src/books_http_handler.erl:30` `parse_qs(#{qs:=Qs})->Qs` matches every real Req, because Cowboy's Req has `qs => binary` (cowboy_http.erl:829). `proplists:get_value/2` on a binary crashes with function_clause. Live, with a row in the DB: `GET /books` → 500 and `GET /books?author=B` → 500. |

## Requirements

| ID | Requirement | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates | ✗ missing | crashes, see above; `books_db:create` works only when called directly (database_crud_test) |
| R2 | GET /books lists | ✗ missing | live 500 |
| R3 | ?author= filter | ✗ missing | live 500; the DB-layer filter at books_db.erl:22 is never reached |
| R4 | GET /books/{id} | ✓ implemented | live 200 with JSON; 404 `{"error":"not_found"}` for id 99 |
| R5 | PUT /books/{id} | ✗ missing | live 500 (same badmatch) |
| R6 | DELETE /books/{id} | ✓ implemented | live 204; 404 path at books_db.erl:30 |
| R7 | SQLite | ✓ implemented | books_db.erl:39-46, `sqlite3 -json` CLI against books.db |
| R8 | JSON + status codes | ~ partial | correct on health/get/delete; crashing routes return an empty 500 |
| R9 | title/author validation (400) | ~ partial | `decode_book` books_http_handler.erl:20 is unit-tested, but over HTTP the 400 is unreachable (POST crashes first) |
| R10 | GET /health | ✓ implemented | live 200 `{"status":"ok"}` |
| R11 | README | ✓ implemented | README.md covers setup, run, endpoints and tests |
| R12 | ≥3 tests | ✓ implemented | 4 eunit tests in test/books_api_tests.erl, test_coverage=1.0 |

requirement_coverage = 6/12 = **0.50**

## Build & Test

These were not re-run; the stored scores are `{"test_coverage":1.0,"defect_rate":1.0,"code_quality":1.0}`. The live probe ran on a temp copy (`rebar3 compile`, app started on port 18085, then curl).

## Metrics

| Metric | Value |
|---|---|
| Source + test LOC | 131 (5 src + 1 test .erl) |
| Dependencies | 2 direct (cowboy 2.12.0, jsx 3.1.0) |
| Tests total / effective | 4 / 4 |
| Skip ratio | 0% |

## Findings

1. [critical] POST/PUT read_body badmatch: create, update and 400 validation are all unreachable
2. [critical] GET /books parse_qs shim: list and filter crash
3. [high] Test-only branches in production code (`test_request`, map-pattern shims) make the HTTP "contract" test vacuous. This is why the tests pass despite the bugs. FEEDBACK.md explicitly asked for an HTTP-layer test.
4. [medium] R8 holds only on the non-crashing routes

## Reproduce

```bash
T=$(mktemp -d); cp -R src test rebar.config rebar.lock _build $T/; cd $T; rebar3 compile
erl -noshell -pa _build/default/lib/*/ebin -eval 'application:load(books_api), application:set_env(books_api,port,18085), application:set_env(books_api,db_path,"b.db"), application:ensure_all_started(books_api), timer:sleep(8000), init:stop().' &
sleep 3; curl -s -w ' %{http_code}\n' http://127.0.0.1:18085/books
curl -s -w ' %{http_code}\n' -X POST -H 'content-type: application/json' -d '{"title":"Dune","author":"FH"}' http://127.0.0.1:18085/books
```
