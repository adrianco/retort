# Evaluation: erlang · hermes-local · Qwen3-Coder-Next-4bit · prompt=repair · rep 1

## Summary

- **Factors:** language=erlang, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=repair, stack=m80
- **Status:** ok (builds; runs; HTTP layer non-functional)
- **Requirements:** 4/12 implemented, 6 partial, 1 missing (R7, R10, R11, R12 met)
- **Tests:** partial — test_coverage=0.5454 (build clean, some assertions fail); no skips
- **Build:** pass — code_quality=1.0, defect_rate=1.0 (from scores.json)
- **Lint:** pass — code_quality=1.0
- **Architecture:** see `summary/`
- **Findings:** 9 items in `findings.jsonl` (0 critical, 7 high, 2 medium)
- **requirement_coverage:** 0.3333 (4/12)

## Second-opinion verdict: the first evaluation was CORRECT

This is a re-check of a prior evaluation that scored `requirement_coverage=0.3333` and
claimed R1, R3, and R8 were not met. I went to the code to try to find the "missing"
implementations. **All three claims are CONFIRMED.** The handler genuinely calls
functions that do not exist in the pinned cowboy version — this is not a case of code
living in another file.

| First evaluator's claim | Verdict | What I checked |
|----|----|----|
| **R1** — all /books routes crash: handler calls nonexistent `cowboy_req:match_params/1` | **CONFIRMED** | `src/book_api_handler.erl:9` calls `cowboy_req:match_params(Req0)`. Grepped `_build/default/lib/cowboy/src/cowboy_req.erl` (cowboy 2.10.0, pinned in rebar.lock): **0 occurrences** of `match_params`. Its `-export` list has only `binding/2,3`, `bindings/1`, `match_qs/2`, `parse_qs/1`, `qs/1`. `init/2` raises `undef` on every request before dispatch. (Evaluator said line 8; it is line 9 — trivial off-by-one.) |
| **R3** — `?author=` filter: nonexistent `cowboy_req:query_param/2` + type mismatch | **CONFIRMED** | `src/book_api_handler.erl:39` calls `cowboy_req:query_param(<<"author">>, Req)` — **0 occurrences** in cowboy_req.erl. Also unreachable (init crashes first). Also line 41 `binary_to_list(AuthorVal)` → string, then line 61 `=:=` against the binary the DB returns → never matches. |
| **R8** — JSON never decoded to maps; `jiffy:decode/1` without return_maps → is_map guard never matches; atom vs binary keys | **CONFIRMED** | `src/book_api_handler.erl:19,93` call `jiffy:decode(Body)` with no `[return_maps]`. Default jiffy returns ejson `{[...]}` (a tuple, not a map), so the `is_map(Decoded)` guards at lines 24/98 never match → `function_clause`. `src/book_api_db.erl:134,172` use atom keys `maps:get(title, Attrs)`; binary JSON keys would `badkey`. (Evaluator cited db line 113; actual sites are 134/172 — line number off, defect real.) |

**Why the tests don't catch this:** `test/book_api_integration_tests.erl` and
`test/book_api_db_tests.erl` call `book_api_db` **directly** with atom-keyed maps
(`#{title => <<"...">>, author => <<"...">>}`) and grep shows **0** references to
`book_api_handler` or `cowboy` in the tests. They exercise the DB layer, so the HTTP
handler's `undef`/`function_clause` crashes are invisible to the suite — which is exactly
how a repair run can "pass some tests" while leaving the FEEDBACK defect unfixed.

**Conclusion:** the repair prompt asked to fix the dead HTTP path; it was **not fixed**.
The re-scored `requirement_coverage` is **0.3333**, matching the first evaluation.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | Route + `book_api_db:create_book/1` exist, but `book_api_handler.erl:9` `match_params/1` undef kills the HTTP path |
| R2 | GET /books lists all | ~ partial | `handle_books_collection_request(<<"GET">>,_):38` correct but unreachable — init crashes at `:9` |
| R3 | GET /books ?author= filter | ✗ missing | `book_api_handler.erl:39` nonexistent `query_param/2`; unreachable; binary/list type mismatch at `:41`/`:61` |
| R4 | GET /books/{id} | ~ partial | `handle_book_request(<<"GET">>,…):76` correct but init crashes at `:9` |
| R5 | PUT /books/{id} | ~ partial | Dead at `:9`; also `jiffy:decode`/is_map crash at `:93`/`:98` |
| R6 | DELETE /books/{id} | ~ partial | `handle_book_request(<<"DELETE">>,…):116` correct but init crashes at `:9` |
| R7 | SQLite / embedded DB | ✓ implemented | `book_api_db.erl:30-37` uses `sqlite3:open`/`sql_exec`; real table DDL |
| R8 | JSON responses + status codes | ~ partial | Handlers build JSON replies (201/200/404/400/405) but write/read paths crash pre-reply; only `/health` returns JSON over HTTP |
| R9 | Validation: title & author required | ~ partial | `book_api_db.erl:248 validate_book/1` sound and called at `:139`, but HTTP create path dead (R1) |
| R10 | GET /health | ✓ implemented | `book_api_health.erl:init/2` — no `match_params`; returns 200 `{status:healthy}` |
| R11 | README with setup & run | ✓ implemented | `README.md` documents rebar3 compile / eunit / run |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 `_test_()` generators in `book_api_db_tests.erl` + 5 in integration tests; test_coverage=0.5454 > 0 |

Implemented = R7, R10, R11, R12 → **4/12 = 0.3333**.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality:     1.0     (build + lint clean)
defect_rate:      1.0     (compiles)
test_coverage:    0.5454  (tests run; ~half of assertions pass; 0 skips)
maintainability:  0.8541
idiomatic:        0.93
token_efficiency: 0.0
```

The build is clean and tests execute — the failure mode is **runtime**, in the untested
HTTP handler, not a compile error.

## Metrics

| Metric | Value |
|--------|-------|
| Source modules | 6 (`src/*.erl`) + 3 test modules |
| cowboy version | 2.10.0 (rebar.lock) |
| Tests total | 11 generators (6 db + 5 integration) |
| Skips | 0 |
| test_coverage | 0.5454 |
| requirement_coverage | 0.3333 (4/12) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] R1 — POST /books dead: `cowboy_req:match_params/1` undef (`book_api_handler.erl:9`)
2. [high] R3 — `?author=` filter: nonexistent `query_param/2` + unreachable + type mismatch
3. [high] R8 — `jiffy:decode` without return_maps → is_map guard never matches (function_clause)
4. [high] R2/R4/R6 — list, get-by-id, delete all dead over HTTP via the same `:9` crash
5. [medium] test-fail-1 — test_coverage=0.5454; tests bypass the handler so they miss the HTTP defects

## Reproduce

```bash
RD="experiments/adrianco/experiment-41-repair-80b-fullctx/bookshop/runs/agent=hermes-local_language=erlang_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=repair_stack=m80/rep1"
# Confirm the handler calls functions that do not exist in cowboy 2.10.0:
grep -n "match_params\|query_param\|jiffy:decode" "$RD/src/book_api_handler.erl"
grep -c "match_params\|query_param" "$RD/_build/default/lib/cowboy/src/cowboy_req.erl"   # -> 0 and 0
grep -E "^-export" "$RD/_build/default/lib/cowboy/src/cowboy_req.erl" | grep -E "binding|match_qs|parse_qs"
# Confirm tests never touch the handler:
grep -c "book_api_handler\|cowboy" "$RD"/test/*.erl   # -> 0
cat "$RD/scores.json"
```
