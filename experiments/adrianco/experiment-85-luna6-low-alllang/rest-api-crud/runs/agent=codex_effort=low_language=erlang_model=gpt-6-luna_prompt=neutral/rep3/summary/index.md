# Architecture Summary — Books REST API (Erlang/OTP)

A small OTP application exposing a CRUD REST API for a book collection over a
hand-rolled HTTP/1.1 server, persisting to SQLite via the `sqlite3` CLI.

## Modules

| Module | Role |
|--------|------|
| `books_app` | OTP `application` callback; starts the supervisor. |
| `books_sup` | `one_for_one` supervisor; reads `port`/`db_path` from app env and starts the store then the HTTP listener. |
| `books_http` | `gen_server` TCP acceptor + hand-written HTTP/1.1 parser and router. `request/4` is the pure routing core (directly unit-tested). |
| `books_store` | `gen_server` serializing all DB access; builds SQL and shells out to `sqlite3 -json`. Exposes `create/1,list/1,get/1,update/2,delete/1`. |
| `books_json` | Dependency-free JSON encoder/decoder (object/array/string/number). |

## Request flow

1. `books_http:init/1` listens on the port; each accepted socket is served in a
   spawned process (`serve/1`).
2. `read_request/1` parses request line + headers, reads the body by
   `Content-Length`, then calls `request/4`.
3. `request/4` dispatches on method + path segments to `books_store`, validating
   the JSON body (`with_valid_book`) and id (`with_id`) first.
4. `books_store` assembles SQL (string interpolation with `sql_value` quoting),
   runs it through the `sqlite3` port, and decodes the JSON result back via
   `books_json`.
5. `send_response/3` serializes the reply map to JSON with status line and
   `Connection: close`.

## Interfaces / endpoints

`GET /health`, `POST /books`, `GET /books` (+`?author=`), `GET /books/{id}`,
`PUT /books/{id}`, `DELETE /books/{id}` (204 on success).

## Notes

- Single `books_store` gen_server serializes DB access — correct but a
  throughput bottleneck.
- Persistence is a real file-backed SQLite DB (not in-memory), satisfying R7.
- No external deps (`rebar.config` deps `[]`); `warnings_as_errors` is on and the
  build is clean.
