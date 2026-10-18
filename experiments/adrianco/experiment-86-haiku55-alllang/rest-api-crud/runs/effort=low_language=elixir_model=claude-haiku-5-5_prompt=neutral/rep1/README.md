# Book API

A REST API for managing a book collection, built with Elixir, Plug, Bandit and SQLite
(via `exqlite`). Data is stored in a local SQLite file.

## Requirements

- Elixir 1.15+ and Erlang/OTP 25+
- A C compiler (needed by `exqlite` to build SQLite)

## Setup

```sh
mix deps.get
```

## Run

```sh
mix run --no-halt          # listens on port 4000
PORT=8080 mix run --no-halt  # custom port
```

The database lives at `data/book_api.db` and is created automatically.

## Test

```sh
mix test
```

Tests use `data/book_api_test.db` and do not start the HTTP server.

## API

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | /books        | Create a book                                | 201     |
| GET    | /books        | List books; optional `?author=` (case-insensitive) | 200 |
| GET    | /books/{id}   | Get one book                                 | 200     |
| PUT    | /books/{id}   | Replace a book's fields                      | 200     |
| DELETE | /books/{id}   | Delete a book                                | 204     |
| GET    | /health       | Health check (verifies DB connectivity)      | 200     |

Book fields: `title` (required), `author` (required), `year` (optional integer 0–9999),
`isbn` (optional string). `id` is assigned by the server.

Errors are JSON: `404 {"error":"not_found"}`, `422 {"error":"validation_failed","details":{...}}`,
`400 {"error":"invalid_json"}`.

### Examples

```sh
curl -i -X POST localhost:4000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'localhost:4000/books?author=Frank%20Herbert'
curl -X PUT localhost:4000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:4000/books/1
curl localhost:4000/health
```
