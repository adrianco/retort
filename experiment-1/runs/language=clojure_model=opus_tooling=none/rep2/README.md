# Books API

A REST API for managing a book collection, built in Clojure with Ring/Jetty, Compojure, and SQLite (via next.jdbc).

## Requirements

- Java 11+
- Clojure CLI (`clojure` / `clj`)

## Run

```
clojure -M:run
```

The server listens on port 3000 (override with `PORT`). Data is stored in `books.db` in the current directory.

## Endpoints

- `GET  /health` — health check
- `POST /books` — create book. Body: `{"title","author","year","isbn"}`. `title` and `author` required.
- `GET  /books` — list books. Optional `?author=` filter.
- `GET  /books/{id}` — get one book.
- `PUT  /books/{id}` — update a book.
- `DELETE /books/{id}` — delete a book.

## Test

```
clojure -M:test
```
