# Books API (Erlang)

A small JSON REST service for a book collection. It runs on OTP with Cowboy and stores records in SQLite using the `sqlite3` command line client.

## Requirements

- Erlang/OTP 25 or newer
- rebar3
- SQLite 3 (`sqlite3` on `PATH`)

## Run

```sh
rebar3 get-deps
rebar3 shell
```

The service listens on port `8080` and creates `books.db` in its working directory. Override the settings when starting the application with `application:set_env(books_api, port, 9090)` and `application:set_env(books_api, db_path, "/path/to/books.db")` before `application:ensure_all_started(books_api)`.

## Endpoints

- `GET /health` — health status
- `POST /books` — create JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "..." }`; returns `201`
- `GET /books` — list books; optionally filter with `?author=Frank%20Herbert`
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book using the same JSON fields as create
- `DELETE /books/{id}` — delete a book; returns `204`

Title and author must be non-empty strings. Missing optional year and ISBN values are stored as null and an empty string respectively. Invalid JSON or missing required values returns `400`; unknown IDs return `404`.

## Tests

```sh
rebar3 eunit
```

