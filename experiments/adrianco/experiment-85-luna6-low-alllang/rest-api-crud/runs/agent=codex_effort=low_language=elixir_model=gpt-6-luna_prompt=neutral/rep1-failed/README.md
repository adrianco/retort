# Book API

A small JSON REST API for managing a book collection, built with Elixir, Plug/Cowboy, and SQLite.

## Requirements

- Elixir 1.16 or newer
- Erlang/OTP

## Setup and run

```sh
mix deps.get
mix test
mix run --no-halt
```

The server listens on port `4000` and stores data in `books.db` in the current directory. Set `PORT` or `BOOKS_DB` to change these values.

## API

- `GET /health` — health status
- `POST /books` — create a book (`title` and `author` required; `year` and `isbn` optional)
- `GET /books` — list all books; optionally filter with `?author=Name`
- `GET /books/:id` — retrieve a book
- `PUT /books/:id` — replace a book's fields (`title` and `author` required)
- `DELETE /books/:id` — delete a book

All responses use JSON. Create returns `201`; successful reads, updates, and deletes return `200`; invalid input returns `400`; missing books return `404`.

Example:

```sh
curl -i -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```
