# Book collection API

A small Objective-C HTTP service using Foundation and SQLite. Requires macOS, Xcode Command Line Tools, and Python 3 for tests.

```sh
make
./books
make test
```

The server listens on port 8080 by default. Set `PORT` to change it and `BOOKS_DB` to select the SQLite file (default: `books.sqlite3` in the current directory). Data persists across restarts.

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with an `id` and status 201.
- `GET /books` returns an array; `?author=...` filters by exact, case-sensitive author.
- `GET /books/{id}` returns one book.
- `PUT /books/{id}` replaces the book's fields and returns the updated book.
- `DELETE /books/{id}` removes it and returns 204 with an empty body.

Create and update bodies are JSON objects with non-blank string `title` and `author`. `year` is optional/null or an integer from 1 through 9999; `isbn` is optional/null or a string. Missing optional fields become null. Invalid input returns 400, missing resources 404, unsupported methods 405, and database errors 500. Error bodies are JSON objects with an `error` string.

Example:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:8080/books?author=Octavia%20Butler'
```
