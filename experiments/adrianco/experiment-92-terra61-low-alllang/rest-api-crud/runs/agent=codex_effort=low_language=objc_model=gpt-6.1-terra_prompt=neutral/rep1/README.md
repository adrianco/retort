# Books API

A small Objective-C HTTP service backed by SQLite. It uses macOS Foundation and the system SQLite library; no third-party packages are required.

## Build and run

Install Xcode Command Line Tools, then run:

```sh
make
./books-server
```

The server listens on port 8080 on all interfaces. Set `PORT` to choose another port and `BOOKS_DB` to choose the SQLite database path (default: `books.sqlite3` in the current directory). The database and table are created automatically.

```sh
PORT=8081 BOOKS_DB=/tmp/books.db ./books-server
make test
```

Tests require Python 3 and start the service with an isolated temporary database.

## API

All responses are JSON. Errors use `{"error":"message"}`.

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with its generated `id` (201).
- `GET /books` returns an array ordered by ID. `?author=...` filters by exact author; URL-encode the value.
- `GET /books/{id}` returns one book.
- `PUT /books/{id}` replaces the book and returns it.
- `DELETE /books/{id}` deletes the book and returns `{"deleted":true}`.

For POST and PUT, send a JSON object with nonblank string `title` and `author`. `year` is an optional integer and `isbn` is an optional string; either may be null. Omitted optional fields become null, including on PUT. Invalid input returns 400, a missing book or route returns 404, and an unsupported method returns 405.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:8080/books?author=Octavia%20Butler'
```
