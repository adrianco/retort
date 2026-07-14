# BookApi

A small REST API for managing a book collection, built in Elixir with Plug/Cowboy and SQLite (via [`exqlite`](https://hex.pm/packages/exqlite)).

## Requirements

- Elixir ~> 1.15 (tested with 1.19)
- Erlang/OTP 25+

## Setup

```sh
mix deps.get
mix compile
```

## Run

```sh
mix run --no-halt
```

The server listens on port `4000` by default and stores data in `books.db` in the working directory. Override via application config or env if needed.

## Run tests

```sh
mix test
```

## Endpoints

| Method | Path              | Description                                  |
|--------|-------------------|----------------------------------------------|
| GET    | `/health`         | Health check, returns `{"status":"ok"}`      |
| GET    | `/books`          | List all books. Supports `?author=` filter   |
| GET    | `/books/:id`      | Fetch a single book                          |
| POST   | `/books`          | Create a book (JSON body)                    |
| PUT    | `/books/:id`      | Update a book (partial JSON body allowed)    |
| DELETE | `/books/:id`      | Delete a book                                |

### Book payload

```json
{
  "title":  "string (required)",
  "author": "string (required)",
  "year":   2024,
  "isbn":   "string"
}
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `404 Not Found` — unknown id or unknown route
- `422 Unprocessable Entity` — validation failure (missing required field)

### Examples

```sh
curl -s http://localhost:4000/health

curl -s -X POST http://localhost:4000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl -s 'http://localhost:4000/books?author=Frank%20Herbert'

curl -s -X PUT http://localhost:4000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2020}'

curl -s -X DELETE http://localhost:4000/books/1
```

## Project layout

```
lib/book_api/
  application.ex   # OTP supervisor: starts Repo + Cowboy
  repo.ex          # GenServer wrapping a single Exqlite connection
  books.ex         # CRUD + validation
  router.ex        # Plug.Router with the REST endpoints
config/config.exs  # port + db_path; test env uses books_test.db on port 4002
test/              # Plug.Test-based integration tests
```
