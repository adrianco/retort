# Book Collection API

A small JSON REST API built with Elixir/OTP and SQLite. It uses the system `sqlite3` command-line client, so no Hex dependencies are needed.

## Requirements

- Elixir and Erlang/OTP
- SQLite 3 (`sqlite3` available on `PATH`)

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 by default. Set `PORT` to change it and `BOOKS_DB` to choose the SQLite database path.

## Routes

- `GET /health`
- `POST /books` with JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "..." }`
- `GET /books?author=Frank%20Herbert`
- `GET /books/:id`
- `PUT /books/:id` with the same JSON fields
- `DELETE /books/:id`

Title and author are required for create and update. Create returns 201, reads and updates return 200, deletion returns 204, invalid input returns 422, and missing books return 404.

## Tests

```sh
mix test
```
