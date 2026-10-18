# Book API

A small JSON REST API for a book collection. It is written in Elixir and uses SQLite for persistent storage. The project has no Hex dependencies; it expects Elixir/OTP and the `sqlite3` command line utility to be installed.

## Run

```sh
mix run --no-halt
```

The service listens on port `4000` by default and stores its database in `data/books.sqlite3`. Set `PORT` and `DATABASE_PATH` to override these values.

## Endpoints

- `GET /health`
- `POST /books` with JSON fields `title`, `author`, and optional `year`, `isbn`
- `GET /books` (optional `?author=...` filter)
- `GET /books/:id`
- `PUT /books/:id` with the complete book representation
- `DELETE /books/:id`

Creation returns `201`, successful reads and updates return `200`, deletion returns `204`, invalid JSON returns `400`, invalid required fields return `422`, and missing books return `404`.

Example:

```sh
curl -X POST http://localhost:4000/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}'
```

## Tests

```sh
mix test
```
