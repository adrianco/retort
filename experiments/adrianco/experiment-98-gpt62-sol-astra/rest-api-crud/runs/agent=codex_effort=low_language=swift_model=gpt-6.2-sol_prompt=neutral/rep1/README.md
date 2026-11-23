# Book Collection API

A Swift REST service with SQLite storage. It uses Apple's Network framework and the system SQLite library.

## Setup and run

Use macOS 12 or later with a Swift 5.9 or newer toolchain and a macOS SDK (Xcode or the Xcode Command Line Tools). From this directory:

```sh
swift build
swift test
swift run book-server
```

The server listens on port 8080 and saves the collection to `books.sqlite` in the working directory. Set `PORT` or `BOOK_DB_PATH` to override those defaults. If the database path includes a directory, create that directory before starting the server.

## Endpoints

| Method and path | Result |
| --- | --- |
| `GET /health` | `200` with `{"status":"ok"}` |
| `POST /books` | `201` with the created book and a `Location` header |
| `GET /books` | `200` with a JSON array ordered by ID. Use `?author=Octavia%20Butler` for an exact, case-sensitive author match. |
| `GET /books/{id}` | `200` with the requested book |
| `PUT /books/{id}` | `200` with the replaced book, using the same ID |
| `DELETE /books/{id}` | `204` with an empty response body |

Send a JSON object for POST and PUT. Both require nonblank string values for `title` and `author`. The optional fields are an integer `year` and a string `isbn`. Omitted or null optional fields are cleared on PUT and omitted from response objects. Book IDs are positive integers assigned by the server.

Invalid book input or a malformed ID returns `400`. A valid ID with no matching book returns `404`. Error bodies are JSON objects with an `error` field. The server closes the connection after each response and accepts request bodies up to 1 MiB using `Content-Length`.

```sh
curl -i http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:8080/books?author=Octavia%20Butler'
```
