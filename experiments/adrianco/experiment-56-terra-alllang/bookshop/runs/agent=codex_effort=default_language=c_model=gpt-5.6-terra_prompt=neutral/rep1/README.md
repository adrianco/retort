# Book Collection API

A small REST API written in C with SQLite persistence.

## Build and run

```sh
make
./book_api 8080 books.db
```

The port and database path are optional; their defaults are `8080` and `books.db`.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book. JSON requires `title` and `author`; optional `year` and `isbn` default to zero and an empty string.
- `GET /books` lists books. `GET /books?author=Name` filters by exact author.
- `GET /books/{id}` retrieves a book.
- `PUT /books/{id}` replaces a book (also requires title and author).
- `DELETE /books/{id}` deletes a book.

Example:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

Responses are JSON. Successful creates return 201; missing resources return 404; invalid book data returns 400.

## Tests

```sh
make test
```

This runs portable unit tests for validation and JSON handling. In an environment
that permits listening on loopback ports, `make integration-test` runs end-to-end
checks for health, creation, author filtering, validation, update, deletion, and
not-found handling.
