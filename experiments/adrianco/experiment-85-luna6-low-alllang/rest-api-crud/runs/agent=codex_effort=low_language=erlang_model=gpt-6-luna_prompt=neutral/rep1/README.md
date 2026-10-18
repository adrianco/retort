# Books API (Erlang)

A small JSON REST API for managing books, built with Erlang/OTP, Cowboy, and SQLite.

## Requirements

- Erlang/OTP 25 or newer
- rebar3
- `sqlite3` on `PATH`

## Run

```sh
rebar3 get-deps
rebar3 shell
```

The server listens on port 8080 by default and stores records in `books.db`. Configure these with application environment values `port` and `database` in `sys.config`.

## Endpoints

- `GET /health`
- `POST /books` with JSON `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`
- `GET /books` (optional `?author=Frank%20Herbert`)
- `GET /books/{id}`
- `PUT /books/{id}` with the same book JSON fields
- `DELETE /books/{id}`

Title and author are required for create and update. Responses use JSON and conventional HTTP status codes (`201` for create, `404` for missing records, and `400` for invalid input).

## Tests

```sh
rebar3 eunit
```
