# Architecture Summary — book_api (Erlang/OTP)

Standard rebar3 OTP application. Entry point `book_api_app` starts `book_api_sup`,
a `one_for_one` supervisor with two permanent workers:

- **`book_api_db`** (`gen_server`) — persistence layer over `esqlite` (SQLite).
  Creates the `books` table on `init/1`, then serves CRUD via `handle_call`:
  `create_book/1`, `get_book/1`, `get_books/1` (with `?author=` variant),
  `update_book/2` (dynamic `SET` clause), `delete_book/1`, and `health_check/0`.
  Opens/closes a fresh connection per call. Records defined in `book_api_db.hrl`.
- **`book_api_routes`** — HTTP layer. Compiles a Cowboy router for `/health`,
  `/books`, `/books/:id`, and dispatches by method in `handle_request/3`. Encodes
  responses with `jsx`. Contains `validate_book_params/1` (title+author required).

## Module map

| Module | Role |
|--------|------|
| `book_api_app` | OTP application callback |
| `book_api_sup` | Supervisor (db + routes workers) |
| `book_api_db` | gen_server + SQLite CRUD |
| `book_api_routes` | Cowboy HTTP handlers + validation |
| `book_api_db.hrl` | `#book{}` record |
| `book_api_unit_tests` | EUnit tests (validation only) |

## Deps (rebar.config)

cowboy 2.10.0, esqlite 0.8.3, jsx 3.1.0.

## Key risks (see evaluation.md)

1. **Routes module mixes Cowboy 1.x and 2.x APIs** — `-behaviour(cowboy_http_handler)`,
   `handle/2`, `cowboy_req:body/1`, `cowboy_req:query_params/1`, and an `init/2`
   returning a 2-tuple are all Cowboy 1.x idioms incompatible with the declared
   cowboy 2.10.0. The HTTP layer compiles but would not serve requests at runtime.
2. **EUnit tests never execute** — the generator is exported as `unit_tests_/0`,
   which does not match EUnit's `*_test_/0` discovery suffix; the 4 assertions are
   dead code. They also test a *copied* `validate_book_params/1`, not the real module.
3. **No HTTP status codes** — every response defaults to 200, including create,
   validation errors, and not-found.
