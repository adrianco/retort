# Books API

A small C HTTP/1.1 service backed by SQLite. It requires a C11 compiler, SQLite 3, json-c, and pkg-config; Python 3 is needed to run the tests. Install the SQLite and json-c development packages for your system (for example, `brew install sqlite json-c pkg-config` on macOS or `apt install libsqlite3-dev libjson-c-dev pkg-config` on Debian/Ubuntu).

```sh
make
./books-api
make test
```

The server listens on port 8080 by default. Set `PORT` to choose another port and `BOOKS_DB` to choose the SQLite database path (default `books.db`). The database and table are created automatically. Stop the server with Ctrl-C.

All responses are JSON. `GET /health` returns `{"status":"ok"}`. The collection endpoints are:

- `POST /books`: create a book; returns 201 and the saved object.
- `GET /books`: return an array ordered by ID. `?author=...` filters by exact author (URL-encode the value).
- `GET /books/{id}`: return one book.
- `PUT /books/{id}`: replace a book's fields and return the saved object.
- `DELETE /books/{id}`: delete a book and return `{"deleted":true}`.

Create and update bodies are JSON objects with nonblank string `title` and `author`; `year` is an optional integer and `isbn` an optional string. Missing or null optional fields are stored as null. Invalid input returns 400, unknown resources return 404, and unsupported methods return 405. For example:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:8080/books?author=Octavia%20Butler'
```
