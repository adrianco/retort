# Books API (Elixir)

REST API for a book collection using Plug + Cowboy, stored in SQLite (Exqlite).

## Setup & run
```
mix deps.get
mix run --no-halt        # listens on PORT (default 4000), DB file BOOKS_DB (default books.db)
```

## Endpoints
- `GET /health`
- `POST /books` — JSON `{title, author, year, isbn}`; title/author required (422 otherwise)
- `GET /books[?author=Name]`
- `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id` (404 if missing, 204 on delete)

## Tests
```
mix test   # uses an in-memory SQLite DB
```
