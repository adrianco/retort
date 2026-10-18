# Objective-C Book Service

A small JSON REST service written in Objective-C using macOS Foundation and SQLite.

## Requirements

- macOS with Xcode Command Line Tools (Clang and Foundation)
- SQLite (included with macOS)

## Build and run

```sh
make
./book-service --port 8080 --db books.sqlite
```

The service listens on `127.0.0.1`. Use `--port 0` to select an available port (the chosen port is printed at startup). The database file is created automatically.

## Endpoints

- `GET /health` — `{"status":"ok"}`
- `POST /books` — JSON with required nonblank `title`, `author`; optional `year`, `isbn`; returns `201` and the created object.
- `GET /books` — list books; optional `?author=` substring filter.
- `GET /books/{id}` — return one book or `404`.
- `PUT /books/{id}` — replace a book's fields; requires `title` and `author`.
- `DELETE /books/{id}` — delete a book; returns `204` or `404`.

Errors return a JSON object with an `error` message. For example:

```sh
curl -X POST http://127.0.0.1:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'
```

## Tests

```sh
make test
```

The integration test uses a temporary SQLite database and covers health, validation, create, filtered list, read, update, delete, and not-found behavior.
