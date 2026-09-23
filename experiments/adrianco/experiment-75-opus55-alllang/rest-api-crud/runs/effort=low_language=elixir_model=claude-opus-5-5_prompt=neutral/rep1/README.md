# Books API (Elixir)

REST API for a book collection using Plug + Bandit, with SQLite storage (exqlite).

## Setup & run

```sh
mix deps.get
mix run --no-halt            # listens on PORT (default 4000), DB file BOOKS_DB (default books.db)
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year, isbn}`; title & author required → 201 / 422 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/:id | 200 / 404 |
| PUT | /books/:id | full replace, same validation → 200 / 404 / 422 |
| DELETE | /books/:id | 204 / 404 |

Example: `curl -XPOST localhost:4000/books -H 'content-type: application/json' -d '{"title":"Dune","author":"Frank Herbert"}'`

## Tests

```sh
mix test
```
Tests use an in-memory SQLite database.
