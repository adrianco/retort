# Book Collection API

A small C++17 REST service backed by SQLite.

## Build and run

The system SQLite development library is required. On macOS: `brew install sqlite` if it is not already available.

```sh
make
./book_api 8080 books.db
```

The optional arguments are port and database path. The server listens on all interfaces.

## API

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book from JSON containing required `title` and `author`, plus optional `year` and `isbn`.
- `GET /books` lists books; `GET /books?author=Name` filters by exact author.
- `GET /books/{id}`, `PUT /books/{id}`, and `DELETE /books/{id}` retrieve, replace, and delete a book.

Successful create/update requests return the book JSON (200); deletion returns 204. Invalid JSON or missing title/author returns 400, and absent resources return 404.

Example:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

```sh
make test
```

The integration-style tests cover health, validation, create/list filtering, update, and deletion.
