# BookApi

A small REST API for managing a book collection, built with Elixir, Plug + Cowboy, Ecto, and SQLite.

## Requirements

- Elixir 1.15+ / OTP 25+
- Mix (ships with Elixir)

## Setup

```sh
mix deps.get
mix ecto.create
mix ecto.migrate
```

## Run

```sh
mix run --no-halt
```

The server listens on port 4000 by default. Configure with the `port` setting in `config/config.exs`.

## API

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | /health        | Health check                             |
| POST   | /books         | Create a book                            |
| GET    | /books         | List books (supports `?author=` filter)  |
| GET    | /books/:id     | Fetch one book                           |
| PUT    | /books/:id     | Update a book                            |
| DELETE | /books/:id     | Delete a book                            |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `404 Not Found` — unknown book or route
- `422 Unprocessable Entity` — validation error

### Examples

```sh
curl -s -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -s 'http://localhost:4000/books?author=Frank%20Herbert'

curl -s http://localhost:4000/books/1

curl -s -X PUT http://localhost:4000/books/1 \
  -H 'content-type: application/json' \
  -d '{"year":1966}'

curl -s -X DELETE http://localhost:4000/books/1

curl -s http://localhost:4000/health
```

## Tests

```sh
mix test
```

Test cases cover the context (`BookApi.Books`) and the HTTP router (`BookApi.Router`), including the health check, CRUD flows, the `?author=` filter, and validation errors.
