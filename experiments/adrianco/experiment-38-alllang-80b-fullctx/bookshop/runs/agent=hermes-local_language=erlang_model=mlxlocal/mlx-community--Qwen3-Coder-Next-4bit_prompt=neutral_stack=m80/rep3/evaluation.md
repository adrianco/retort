# Evaluation: erlang · Qwen3-Coder-Next-4bit (m80) · rep 3

> **SECOND OPINION** — re-check of a prior evaluation that scored
> `requirement_coverage=0.25` and claimed R8-http and R8-status were NOT met.
> **Verdict: the first evaluator was CORRECT on both.** Details under Second-Opinion Verdicts.

## Summary

- **Factors:** language=erlang, agent=hermes-local, model=mlxlocal/Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok (compiles, tests pass) — but HTTP layer non-functional at runtime
- **Requirements:** 3/12 implemented, 9 partial, 0 missing → **requirement_coverage = 0.25**
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — `test_coverage=1.0`, `defect_rate=1.0` from scores.json (not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 11 items in `findings.jsonl` (0 critical, 2 high, 6 medium, 2 low, 1 info)

## Second-Opinion Verdicts

### R8-http — "Cowboy 1.x API against declared cowboy 2.10.0; endpoints non-functional at runtime" → **CONFIRMED (first evaluator was right)**

`rebar.config:2` declares `{cowboy, "2.10.0"}`, but `src/book_api_routes.erl` is written entirely against the **Cowboy 1.x** handler model, which is incompatible with 2.x:

- `book_api_routes.erl:19` — `-behaviour(cowboy_http_handler)`. This behaviour module **does not exist** in Cowboy 2.x (it was removed after 1.x; 2.x uses `cowboy_handler`). Compiles with only a "behaviour undefined" warning.
- `book_api_routes.erl:44-45` — `init(_Transport, _Req) -> {ok, #{}}`. Cowboy 2.x calls `init(Req, State)` and requires a **3-tuple** `{ok, Req, State}`; this returns a 2-tuple → the request process crashes in `cowboy_handler:execute`.
- `book_api_routes.erl:47-55` — `handle/2`. Cowboy 2.x plain handlers have **no `handle/2` callback** (only `init/2`); this function is dead code that is never invoked, so the response body it builds is never sent.
- `book_api_routes.erl:64,97` — `cowboy_req:body/1`. Removed in Cowboy 2.x (replaced by `cowboy_req:read_body/1`) → `undefined function` at runtime.
- `book_api_routes.erl:81` — `cowboy_req:query_params/1`. Does not exist in Cowboy 2.x (2.x uses `cowboy_req:parse_qs/1` / `match_qs/2`) → `undefined function` at runtime.

Grep of `src/` for any Cowboy 2.x API (`read_body`, `cowboy_req:reply`, `parse_qs`, `match_qs`, `cowboy_handler`, `cowboy_rest`) returns **NONE**. The code compiles (remote `Module:Fun` calls are resolved at runtime, and the missing behaviour is only a warning — hence `test_coverage=1.0` on the build gate) but **no HTTP endpoint serves a request correctly at runtime.** First evaluator's evidence is accurate.

### R8-status — "No HTTP status codes set — every response returns 200" → **CONFIRMED (first evaluator was right)**

`handle/2` (`book_api_routes.erl:47-55`) only calls `cowboy_req:set_resp_header/3` + `cowboy_req:set_resp_body/2`; it **never calls `cowboy_req:reply/4`** or sets any status. A grep of all of `src/` for `reply`/`status`/`201`/`404`/`400` finds only:
- JSON **body** fields (`status => <<"ok">>`, `error => <<"not_found">>` …) — not HTTP status,
- `gen_server` `{reply, …}` tuples in `book_api_db.erl` — not HTTP status.

Every branch (create success, `duplicate_isbn`, validation errors, `not_found`) is differentiated only inside the JSON body. R8 requires 201 (create) / 400 (validation) / 404 (not found); **none are present.** First evaluator's evidence is accurate.

**I searched the code for the implementations the first evaluator claimed were missing and confirmed they are genuinely absent** — this is not a first-pass miss.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | Route `book_api_routes.erl:63` + `book_api_db:create_book/1` `book_api_db.erl:69,97` exist, but HTTP layer non-functional at runtime (see R8-http); untested |
| R2 | GET /books lists all | ~ partial | Route `:80` + `book_api_db.erl:129`; non-functional at runtime |
| R3 | GET /books ?author= filter | ~ partial | `book_api_db.erl:77,145` filters by author, but routes.erl:81 uses undefined `cowboy_req:query_params/1` AND `get_books/1` matches atom key `author` while a real qs would give binary keys → filter never fires |
| R4 | GET /books/{id} (+404) | ~ partial | Route `:87`, `{error,not_found}` mapped to JSON body only (`:91`), no 404 status; non-functional at runtime |
| R5 | PUT /books/{id} updates | ~ partial | Route `:95` + `book_api_db.erl:161`; non-functional at runtime |
| R6 | DELETE /books/{id} deletes | ~ partial | Route `:109` + `book_api_db.erl:203`; non-functional at runtime |
| R7 | Data stored in SQLite | ✓ implemented | `book_api_db.erl` — real `esqlite` gen_server, `CREATE TABLE books`, parameterized INSERT/SELECT/UPDATE/DELETE (`:53-214`); esqlite 0.8.3 in rebar.config |
| R8 | JSON + appropriate status codes | ~ partial | JSON via `jsx:encode` present; **no HTTP status codes at all** (see R8-status verdict) |
| R9 | Validation: title & author required | ~ partial | `validate_book_params/1` `book_api_routes.erl:130` exists and IS unit-tested (4 tests), but rejection returns a JSON body not a **400**, and the create path is unreachable at runtime |
| R10 | GET /health | ~ partial | Route `:57` + real `book_api_db:health_check/0` (`SELECT 1`, `:88`); non-functional at runtime |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, build, test, run, curl usage examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/book_api_unit_tests.erl` — 4 eunit tests; `test_coverage=1.0` (run + passed) |

**Tally: 3 implemented, 9 partial, 0 missing → requirement_coverage = 3/12 = 0.25.**

My independent full re-score lands at the same 0.25 the first evaluator reported, though I attribute it to the whole HTTP layer being non-functional (R1–R6, R8, R10 partial) rather than only R8. The build/validation/DB/README/tests deliverables are real; the REST surface that ties them together does not run.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   (build + eunit passed)
defect_rate   = 1.0
code_quality  = 1.0
idiomatic     = 0.94
```

Caveat: `test/book_api_unit_tests.erl` tests a **local copy** of `validate_book_params/1` (`:42-50`), not the real `book_api_routes`/`book_api_db` modules — the agent's own stdout notes an unresolved "eunit discovery" problem. The tests pass but exercise none of the shipped system modules.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test, incl. license headers) | 547 |
| Files (excl. _build/summary) | 19 |
| Dependencies (rebar.config) | 3 (cowboy, esqlite, jsx) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R8-http — HTTP layer uses Cowboy 1.x API against declared cowboy 2.10.0; no endpoint serves at runtime
2. [high] R8-status — no HTTP status codes set anywhere; 201/400/404 absent
3. [medium] R3 — author filter never fires (undefined `query_params/1` + atom/binary key mismatch)
4. [medium] R9 — validation returns JSON body, not 400, and is unreachable at runtime
5. [medium] R1 — POST /books non-functional at runtime (broken handler)

## Reproduce

```bash
cd <run_dir>
grep -n "cowboy_http_handler\|handle/2\|cowboy_req:body\|query_params\|init(_Transport" src/book_api_routes.erl
grep -rniE "read_body|cowboy_req:reply|parse_qs|match_qs|cowboy_handler" src/   # -> NONE (confirms 1.x-only)
grep -n "cowboy" rebar.config                                                    # -> {cowboy, "2.10.0"}
cat scores.json                                                                  # test_coverage=1.0, code_quality=1.0
```
