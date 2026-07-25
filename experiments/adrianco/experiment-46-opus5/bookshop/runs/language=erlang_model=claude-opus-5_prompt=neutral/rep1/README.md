# book_api

A small REST API for managing a book collection, written in Erlang/OTP.

- **HTTP layer:** [Cowboy](https://github.com/ninenines/cowboy) 2.13
- **Storage:** Mnesia `disc_copies` — the transactional embedded database that
  ships with OTP (the Erlang equivalent of an embedded SQLite file). Data is
  written to disk and survives restarts.
- **JSON:** the `json` module built into OTP 27+ — no JSON dependency.

## Requirements

- Erlang/OTP 27 or newer (developed and tested on OTP 29)
- [rebar3](https://rebar3.org)

## Setup and run

```sh
rebar3 compile          # fetch deps and build
rebar3 shell            # run on http://localhost:8080 with an Erlang shell
```

Or build a self-contained release:

```sh
rebar3 release
_build/default/rel/book_api/bin/book_api foreground   # or: start / stop / console
```

Then:

```sh
curl localhost:8080/health
```

### Configuration

| Setting | `config/sys.config` key | Environment variable | Default |
| --- | --- | --- | --- |
| Listen port | `port` | `BOOK_API_PORT` | `8080` |
| Database directory | `db_dir` | `BOOK_API_DB_DIR` | `data` |

The environment variables take precedence, so a second instance is just:

```sh
BOOK_API_PORT=9090 BOOK_API_DB_DIR=/tmp/books-db _build/default/rel/book_api/bin/book_api foreground
```

Port `0` asks the OS for a free port, which is how the test suite runs without
colliding with a development server.

## Tests

```sh
rebar3 eunit
```

47 tests across three suites:

| Suite | Covers |
| --- | --- |
| `test/book_tests.erl` | Validation and rendering rules in isolation — required fields, blank/oversized/non-string input, year range, ISBN-10/13 shapes, UTF-8 and RFC 3339 output. |
| `test/book_store_tests.erl` | Mnesia CRUD — id sequencing, ordering, case-insensitive author lookup, update preserving identity, delete, and durability across a store restart. |
| `test/book_api_http_tests.erl` | The real application over real HTTP: every endpoint, status codes, `Location`/`Allow` headers, error envelopes, unicode round-tripping, the body-size limit and routing failures. |

## API

All responses are `application/json`. Timestamps are RFC 3339 UTC.

### `GET /health`

```json
{"status":"ok","database":"ok","books":2,"uptime_seconds":41}
```

Returns `200`, or `503` with `"status":"error"` if the database is unreachable.
The check reads from Mnesia, so it is a real readiness probe rather than a
"the process is alive" ping.

### `POST /books`

Request body:

```json
{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}
```

| Field | Required | Rules |
| --- | --- | --- |
| `title` | yes | non-blank string, ≤ 512 bytes (trimmed) |
| `author` | yes | non-blank string, ≤ 512 bytes (trimmed) |
| `year` | no | integer between −3000 and 2999, or `null` |
| `isbn` | no | ISBN-10 or ISBN-13 (hyphens and spaces allowed), or `null` |

`201 Created` with the stored book and a `Location: /books/{id}` header.
Omitted optional fields come back as `null`.

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

### `GET /books`

Returns a JSON array ordered by id (i.e. insertion order).

`?author=` narrows the list by exact author name, compared
case-insensitively. A blank value (`?author=`) is treated as "no filter".

```sh
curl 'localhost:8080/books?author=frank%20herbert'
```

### `GET /books/{id}`

`200` with the book, or `404`.

### `PUT /books/{id}`

Replace semantics: the body is validated exactly like `POST`, so `title` and
`author` are required, and **omitting `year` or `isbn` clears them**. The `id`
and `created_at` are preserved; `updated_at` is refreshed.

`200` with the updated book, `400` on validation failure, `404` if absent.

### `DELETE /books/{id}`

`204 No Content` with an empty body, or `404` if it was already gone.

### Status codes

| Code | When |
| --- | --- |
| `200` | successful `GET` / `PUT` |
| `201` | book created |
| `204` | book deleted |
| `400` | malformed/empty JSON body, or failed validation |
| `404` | unknown book id (including non-numeric ids) or unknown route |
| `405` | wrong method for a known route — the `Allow` header lists the valid ones |
| `413` | request body larger than 1 MiB |
| `500` | unexpected server error |
| `503` | health check could not reach the database |

### Error format

Every error uses the same envelope:

```json
{"error":"not_found","message":"Book 42 does not exist"}
```

Validation failures add a `details` array naming each offending field — all of
them, not just the first:

```json
{
  "error": "validation_failed",
  "message": "The book could not be created",
  "details": [
    {"field": "title",  "message": "is required"},
    {"field": "author", "message": "is required"}
  ]
}
```

## Layout

```
include/book_api.hrl        the #book{} record
src/book.erl                pure validation + JSON rendering (no side effects)
src/book_store.erl          Mnesia schema, tables and CRUD
src/book_api_app.erl        application callback, config, routing table
src/book_api_sup.erl        root supervisor
src/book_api_http.erl       shared JSON reply / body-decoding plumbing
src/book_api_books_h.erl    /books           (GET, POST)
src/book_api_book_h.erl     /books/{id}      (GET, PUT, DELETE)
src/book_api_health_h.erl   /health
src/book_api_notfound_h.erl catch-all 404
```

The split keeps the validation rules testable without a database or a socket,
which is why `book_tests.erl` runs in milliseconds while still covering every
rule the HTTP layer enforces.

## Design notes

- **Why Mnesia, not SQLite.** The task allows a "language-equivalent embedded
  DB". Mnesia is exactly that for Erlang: embedded, transactional, on-disk, and
  part of OTP, so there is no NIF to compile or native library to install.
  `book_store` is the only module that knows about it.
- **Ids** come from `mnesia:dirty_update_counter/3`, so they are allocated
  atomically under concurrency and are never reused after a delete — the counter
  is persisted alongside the data.
- **The `book` table is an `ordered_set`**, so listing is already in id order and
  needs no sort.
- **Non-numeric ids return `404`, not `400`.** `/books/abc` cannot name an
  existing resource, and clients handle "this book isn't there" the same way
  regardless of why.
- **Content negotiation is deliberately lenient.** The body is parsed as JSON
  whatever `Content-Type` claims, so `curl -d '{...}'` without an explicit header
  works as expected instead of returning `415`.
