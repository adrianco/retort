# Book collection API

A small Objective-C REST service using Foundation, BSD sockets, and SQLite. It requires macOS, Xcode Command Line Tools, SQLite (included with macOS), and Python 3 for the tests.

```sh
make
./books
# In another terminal:
curl http://localhost:8080/health
make test
```

The server listens on all interfaces on port 8080. Set `PORT` to change the port and `BOOKS_DB` to change the SQLite database path (default: `books.sqlite3` in the current directory). Data persists in that file. Stop the server with Ctrl-C.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:8080/books?author=Octavia%20Butler'
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler"}'
curl -X DELETE http://localhost:8080/books/1
```

`POST /books` creates a book (201); `GET /books` lists books in ID order, optionally filtered by an exact, case-sensitive `author` value; `GET /books/{id}` retrieves one; `PUT /books/{id}` replaces its fields; and `DELETE /books/{id}` deletes it and returns its ID. Successful reads, updates, and deletions return 200. `GET /health` returns `{"status":"ok"}`. All responses are JSON.

Both create and replace require nonblank string `title` and `author`. `year` is optional and must be an integer from 0 through 9999 or null; `isbn` is optional and must be a string or null. Omitted optional fields become null. Invalid input returns 400, missing resources return 404, unsupported methods return 405, and database failures return 500. The server accepts request bodies up to 64 KiB with a Content-Length header; chunked transfer encoding is unsupported. This straightforward single-process server handles one connection at a time and is intended for local or lightweight use.
