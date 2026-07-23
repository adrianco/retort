# Architecture summary — book_api (Erlang)

> Generated inline by `evaluate-run` (the `run-summary` skill was not available in
> the invocable set for this session). Concise, evidence-based module map.

## Modules

| Module | Role | Notes |
|--------|------|-------|
| `book_api` | App entry (`start/0`, `stop/0`) | Starts `crypto`, `inets`, then the `book_api` application. |
| `book_api_app` | OTP `application` behaviour | `start/2` delegates to the supervisor. |
| `book_api_sup` | OTP `supervisor` | one_for_one; children = `book_api_db`, `book_api_http`. |
| `book_api_db` | Storage (gen_server) | **ETS** table `books` + hand-rolled file dump to priv/`/tmp`. Not SQLite. |
| `book_api_http` | HTTP listener | Starts `inets:httpd` on :8080 with `modules=[book_api_http]`. |
| `book_api_handler` | Request routing + bespoke JSON codec | `handle_request/1` dispatches the 6 routes; own JSON encoder/parser. |
| `book` | Book model | `validate/1`, `to_json/1`, `parse_json/1` (binary→atom keys). |

## Request/flow (intended vs actual)

- **Intended:** httpd → `book_api_handler:handle_request/1` → `book_api_db` (ETS) → JSON via `book_api_handler:json_encode/1`.
- **Actual:** `book_api_http` registers itself (`modules=[book_api_http]`) as the httpd mod but exports **no `do/1`** callback, and nothing constructs the bespoke proplist `Req` that `handle_request/1` expects. The handler is therefore **dead code at runtime** — no route is reachable over HTTP.

## Data model

`#{id, title, author, year, isbn}` with binary values. Stored in ETS as `{Id, BookMap}`
tuples — but the table is created with `{keypos, 2}`, so the **map (element 2), not the
Id (element 1), is the key**; integer-Id lookups miss.

## Test surface

- `book_api_test.erl` — real unit tests for `book:validate/1`, `to_json/1`, `parse_json/1`;
  two handler tests are `?assert(true)` placeholders.
- `book_api_integration_test.erl` — app-start smoke + `book:validate` edge cases + db
  invalid-id guards. No HTTP/CRUD-over-the-wire coverage.

## Bottom line

Mechanical gate passes (compiles, `test_coverage=1.0`), but the tests exercise only the
`book`/`book_api_db` module surface. The end-to-end REST path (HTTP wiring + ETS
persistence by id + JSON create) is not functional and not covered. See `findings.jsonl`.
