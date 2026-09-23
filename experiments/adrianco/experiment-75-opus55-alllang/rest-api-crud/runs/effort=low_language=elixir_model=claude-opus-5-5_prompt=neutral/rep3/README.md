# Books API (Elixir)

REST API for a book collection using Plug + Bandit, with SQLite storage (exqlite).

## Setup & run

```sh
mix deps.get
mix run --no-halt          # listens on PORT (default 4000), DB file BOOKS_DB (default books.db)
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 422 if title/author missing |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/:id | 404 if missing |
| PUT | /books/:id | full replace, same validation → 200 |
| DELETE | /books/:id | 204 |

Example: `curl -XPOST localhost:4000/books -H 'content-type: application/json' -d '{"title":"Dune","author":"Frank Herbert","year":1965}'`

## Tests

```sh
mix test    # uses an in-memory SQLite DB
```
