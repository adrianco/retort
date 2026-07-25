# BookApi

A small REST API for managing a book collection, written in Elixir with
[Plug](https://hexdocs.pm/plug) + [Bandit](https://hexdocs.pm/bandit) and backed
by SQLite via [Ecto](https://hexdocs.pm/ecto).

## Requirements

- Elixir ~> 1.20 with Erlang/OTP 26+
- A C toolchain (the `exqlite` dependency compiles the bundled SQLite)

## Setup

```sh
mix setup     # fetches deps, creates the database, runs migrations
```

`mix setup` is an alias for `deps.get` + `ecto.create` + `ecto.migrate`. The
database file lands at `priv/book_api_dev.db` and is gitignored. Since SQLite is
embedded, the application also creates the database file itself at boot if it is
missing — so in practice only `mix deps.get` and `mix ecto.migrate` are strictly
required.

## Run

```sh
mix run --no-halt          # listens on http://localhost:4000
PORT=8080 mix run --no-halt  # or pick a port
```

For an interactive shell alongside the server, use `iex -S mix`.

## Test

```sh
mix test
```

No setup step is needed: `priv/book_api_test.db` is created at boot and
`test/test_helper.exs` migrates it. Each test runs inside an
`Ecto.Adapters.SQL.Sandbox` transaction that is rolled back afterwards, so tests
never see each other's data. The HTTP listener is not started under
`MIX_ENV=test` (`config :book_api, start_server: false`) — router tests drive
`BookApi.Router` directly through `Plug.Test`.

The suite has 37 tests across two files: `books_test.exs` covers the context and
validation rules, `router_test.exs` covers every endpoint over HTTP, including
the error paths (422/400/404/415) and a full create → read → list → update →
delete lifecycle.

## API

All responses are JSON. Errors have the shape
`{"error": "...", "details": {...}}`, where `details` maps field names to a list
of messages.

### `GET /health`

Runs a `SELECT 1` against the database.

```sh
curl localhost:4000/health
# 200 {"status":"ok","service":"book_api"}
```

Returns `503` with `{"status":"degraded"}` if the database is unreachable.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are
optional. Any other keys in the body (including `id`) are ignored.

```sh
curl -X POST localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```
201 Created
Location: /books/1
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,
 "isbn":"9780441013593","inserted_at":"...","updated_at":"..."}
```

### `GET /books`

Lists books, newest first. The optional `?author=` filter is a case-insensitive
substring match.

```sh
curl localhost:4000/books
curl 'localhost:4000/books?author=herbert'
# 200 [ ... ]
```

### `GET /books/:id`

```sh
curl localhost:4000/books/1
# 200 {...}   404 {"error":"Book not found"}
```

### `PUT /books/:id`

Updates a book. Only the fields present in the body are changed, so this also
works as a partial update; the same validation rules as `POST` apply to the
result.

```sh
curl -X PUT localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune (Revised)"}'
# 200 {...}
```

### `DELETE /books/:id`

```sh
curl -i -X DELETE localhost:4000/books/1
# 204 No Content   (404 if it does not exist)
```

## Validation rules

| Field    | Rules |
| -------- | ----- |
| `title`  | required, non-blank after trimming, ≤ 255 chars |
| `author` | required, non-blank after trimming, ≤ 255 chars |
| `year`   | optional integer, `0 < year ≤ 2100` |
| `isbn`   | optional, ISBN-10 (with optional `X` check digit) or ISBN-13, hyphens and spaces allowed, unique across the collection |

Blank/whitespace-only ISBNs are stored as `NULL` so that multiple books without
an ISBN do not collide on the unique index.

## Status codes

| Code | When |
| ---- | ---- |
| 200 | successful `GET` / `PUT` |
| 201 | book created |
| 204 | book deleted |
| 400 | request body is not valid JSON |
| 404 | unknown book id (or unknown route) |
| 415 | `Content-Type` is not `application/json` |
| 422 | body parsed but failed validation |
| 500 | unexpected server error |

## Layout

```
lib/book_api/
  application.ex        supervision tree (Repo + Bandit listener)
  repo.ex               Ecto repo (SQLite adapter)
  router.ex             Plug.Router — all HTTP endpoints
  books.ex              Books context — queries and persistence
  books/book.ex         Ecto schema, changeset, validation
  plugs/json_body.ex    JSON body parsing with 4xx responses on bad input
priv/repo/migrations/   database migrations
test/
  support/api_case.ex   sandbox setup + request/JSON helpers
  book_api/router_test.exs  HTTP-level integration tests
  book_api/books_test.exs   context/validation unit tests
```
