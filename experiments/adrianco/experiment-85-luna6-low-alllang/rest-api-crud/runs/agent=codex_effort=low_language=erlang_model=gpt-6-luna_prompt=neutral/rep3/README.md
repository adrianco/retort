# Books REST API

A small Erlang/OTP REST service for managing books. It uses OTP's TCP sockets for HTTP and SQLite for persistent storage through the `sqlite3` command line client.

## Requirements

- Erlang/OTP 25 or later
- rebar3
- SQLite 3 command line program (`sqlite3`)

## Build and test

```sh
rebar3 compile
rebar3 eunit
```

## Run

```sh
rebar3 shell
```

The service listens on port `8080` and stores the collection in `books.sqlite3` in the current directory. Override either setting when starting the release/shell with Erlang application environment values (`{books, [{port, 9090}, {db_path, "/path/to/books.sqlite3"}]}`).

## Endpoints

- `GET /health`
- `POST /books` with JSON `{"title":"...","author":"...","year":2024,"isbn":"..."}`
- `GET /books` and `GET /books?author=...`
- `GET /books/{id}`
- `PUT /books/{id}` with a complete replacement book object
- `DELETE /books/{id}`

Titles and authors are required. Responses are JSON, with the delete success response using HTTP 204 and an empty body.

## Example

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}'
curl 'http://localhost:8080/books?author=Ursula%20K.%20Le%20Guin'
```
