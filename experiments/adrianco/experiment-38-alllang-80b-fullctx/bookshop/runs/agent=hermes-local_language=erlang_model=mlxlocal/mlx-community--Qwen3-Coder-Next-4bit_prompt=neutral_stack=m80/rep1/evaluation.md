# Evaluation: erlang · Qwen3-Coder-Next-4bit (m80) · rep 1  — SECOND OPINION

## Verdict on the prior evaluation

Re-checked all three claims against the code and the pinned dependency source.
**The first evaluator was correct on all three.** These are genuine runtime crashes.
The subtlety the raw scores hide: `test_coverage=0.8889` / `defect_rate=1.0` do **not**
mean the API works — every test exercises `book_api_db` directly (the gen_server) and
**none** routes a request through cowboy / `book_api_handler`, so the HTTP-layer bugs are
never touched by the test suite. Re-scored `requirement_coverage` independently and landed
on the same **4/12 = 0.3333**.

| Claim | Verdict | Proof |
|-------|---------|-------|
| http-routing: `cowboy_req:match_params/1` does not exist → every /books route crashes | **CONFIRMED** | `grep match_params _build/default/lib/cowboy/src/cowboy_req.erl` → not found; module exports `match_qs/2`, `parse_qs/1`, `binding/2,3`, `bindings/1`. `src/book_api_handler.erl:9` calls it in `init/2`, and `src/book_api_rest.erl:11-12` wires `book_api_handler` to `/books` and `/books/:id` → `error:undef` on every request. |
| http-body: `jiffy:decode/1` returns EJSON, not a map | **CONFIRMED** | `_build/default/lib/jiffy/src/jiffy.erl:55` `decode(Data) -> decode(Data, [])` — no `return_maps`, so objects come back as `{PropList}` (a tuple). `book_api_handler.erl:24,98` guard `Decoded when is_map(Decoded)` → false → `function_clause`. Also `book_api_db.erl:116-119` keys by **atoms** (`maps:get(title, Attrs)`) while `return_maps` would yield **binary** keys → second, independent mismatch. |
| R3 ?author= filter broken (undef query_param + type mismatch) | **CONFIRMED** | `book_api_handler.erl:39` calls `cowboy_req:query_param/2` — not in cowboy 2.10 (`grep` → not found) → crash; `:61` compares `maps:get(author, Book)` (binary from DB) `=:=` `AuthorName` (`binary_to_list` result, a string) → never equal. Both also unreachable behind the line-9 crash. |

The first evaluator did **not** miss any existing implementation here; the burden-of-proof
re-check upholds every claim.

## Summary

- **Factors:** language=erlang, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, prompt=neutral, stack=m80
- **Status:** ok (built + tested) but HTTP API is dead at runtime
- **Requirements:** 4/12 implemented, 7 partial, 1 missing
- **Tests:** 8 test generators, all passing (`test_coverage=0.8889`), 0 skipped — but they test the DB gen_server only, never the HTTP handler
- **Build:** pass — `defect_rate=1.0` from scores.json (Erlang does not check remote-call existence at compile time, so the undef calls compile cleanly)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 6 high, 2 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | route wired + `book_api_db:create_book` tested, but `book_api_handler.erl:9` match_params undef crashes; body parse broken (`:24`) |
| R2 | GET /books lists all | ~ partial | `get_all_books` works+tested; HTTP init crashes at `:9` |
| R3 | GET /books ?author= filter | ✗ missing | `:39` query_param undef + `:61` binary-vs-string mismatch + unreachable |
| R4 | GET /books/{id} | ~ partial | `get_book_by_id` works+tested (incl. 404); id extraction depends on match_params result `#{id := Id}` that never returns |
| R5 | PUT /books/{id} | ~ partial | `update_book` works+tested; HTTP crashes at `:9`; body parse broken (`:98`) |
| R6 | DELETE /books/{id} | ~ partial | `delete_book` works+tested (204/404); HTTP crashes at `:9` |
| R7 | Data stored in SQLite | ✓ implemented | `book_api_db.erl` uses `sqlite3` NIF, real SQL CRUD, tested |
| R8 | JSON responses + status codes | ~ partial | correct reply codes constructed but dead behind crash; only `/health` returns JSON |
| R9 | Validation: title & author required | ~ partial | `book_api_db.erl:208 validate_book` correct but untested (no missing-field test) and HTTP 400 unreachable |
| R10 | GET /health | ✓ implemented | `book_api_health.erl` — separate handler, no match_params, calls `health_check` (tested), 200/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents rebar3 compile / eunit / shell |
| R12 | ≥ 3 tests | ✓ implemented | 8 EUnit generators across 3 files; `test_coverage=0.8889` |

**requirement_coverage = 4/12 = 0.3333** (implemented: R7, R10, R11, R12).

## Build & Test

Not re-run — stored scores from `scores.json`:

```text
code_quality=1.0  test_coverage=0.8889  defect_rate=1.0  maintainability=0.869  idiomatic=0.93
```

`test_coverage=0.8889` reflects the DB-layer EUnit suite passing. It is **not** evidence the
REST API works: the suite calls `book_api_db:*` directly and never issues an HTTP request, so
the `cowboy_req:match_params`/`query_param` undef crashes and the `jiffy` EJSON mismatch are
invisible to it.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test .erl) | 640 |
| Source files | 7 (`src/`) + 3 (`test/`) |
| Dependencies | 3 direct (cowboy 2.10.0, sqlite3 1.1.14, jiffy 1.1.2) |
| Tests total | 8 generators |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R1 — POST /books crashes at runtime (`book_api_handler.erl:9` match_params undef)
2. [high] R2 — GET /books crashes at runtime (same undef)
3. [high] R3 — ?author= filter broken two ways + unreachable (`:39`, `:61`)
4. [high] R4 — GET /books/{id} crashes at runtime
5. [high] R5 — PUT /books/{id} crashes at runtime (undef + jiffy is_map guard)

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=erlang_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
grep -n "match_params" _build/default/lib/cowboy/src/cowboy_req.erl   # -> nothing: function absent
grep -n "query_param" _build/default/lib/cowboy/src/cowboy_req.erl    # -> nothing: function absent
sed -n '55,60p' _build/default/lib/jiffy/src/jiffy.erl                # decode/1 -> decode(Data, []) : no return_maps
grep -n "book_api_handler\|book_api_health" src/book_api_rest.erl     # handler IS the wired route
grep -rn "book_api_db\|cowboy" test/*.erl                             # tests hit the DB only, never cowboy
cat scores.json                                                       # test_coverage 0.8889, defect_rate 1.0
```
