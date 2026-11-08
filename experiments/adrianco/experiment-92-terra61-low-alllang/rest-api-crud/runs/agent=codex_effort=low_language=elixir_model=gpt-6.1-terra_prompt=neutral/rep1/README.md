# Book collection API

An Elixir Plug API backed by SQLite. It creates the database and table automatically on startup.

## Setup and run

Install Elixir 1.15 or later, Erlang/OTP, a C compiler and make. Then run:

```sh
mix deps.get
mix run --no-halt
```

The server listens on port 4000 by default. Set `PORT` to change it and `BOOKS_DB_PATH` to change the database file (default `books.sqlite3`). Run tests with `mix test`; tests use a separate in-memory database.

## API

All request and response bodies are JSON. For example:

```sh
curl -X POST http://localhost:4000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:4000/books?author=Frank%20Herbert'
```

- `POST /books` creates a book and returns 201 and a `Location` header.
- `GET /books` lists books in ID order; the optional `author` query parameter matches exactly.
- `GET /books/:id` returns a book.
- `PUT /books/:id` replaces its fields and returns the updated book.
- `DELETE /books/:id` removes it and returns 204 with an empty body.
- `GET /health` returns `{"status":"ok"}`.

Title and author must be non-empty strings. Year is optional and must be an integer; ISBN is an optional string. Optional fields may be null. Invalid fields return 422, malformed JSON returns 400, and missing books return 404.
