# Book Collection REST API

A small Clojure/Ring service backed by SQLite.

## Run

Requires a Java runtime and the Clojure CLI.

```sh
clojure -M:run
```

The service listens on `http://localhost:3000` and creates `books.db` in the working directory. Set `PORT` and `DATABASE_URL` to override those defaults (for example, `DATABASE_URL=jdbc:sqlite:/tmp/books.db`).

## API

- `GET /health` returns `{ "status": "ok" }`.
- `POST /books` creates a book and returns `201`. JSON fields: `title`, `author` (both required), optional `year` integer and `isbn` string.
- `GET /books` lists books. Use `GET /books?author=Name` to filter by exact author.
- `GET /books/{id}` returns a book or `404`.
- `PUT /books/{id}` fully updates a book using the same validation as create.
- `DELETE /books/{id}` returns `204` or `404`.

Example:

```sh
curl -X POST http://localhost:3000/books \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

## Tests

```sh
clojure -M:test
```
