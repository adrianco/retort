# Book Collection API

A REST API for managing a book collection. It is written in Go with the standard
library's `net/http` router and stores data in SQLite. The SQLite driver is pure Go,
so no C compiler is needed.

## Requirements

- Go 1.26 or newer

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current directory.
Both can be changed with flags:

```sh
go run . -addr :9000 -db /var/lib/books/collection.db
```

The server shuts down gracefully on `Ctrl-C` or `SIGTERM`.

## Test

```sh
go test ./...
```

Add `-race` to also run the race detector. The tests use a temporary SQLite file for each
case, so they leave nothing behind.

## API

All responses are JSON. Errors have the form `{"error": "..."}`. Validation failures
also include a `fields` object that maps each invalid field to a message.

| Method   | Path          | Success                          | Errors                              |
|----------|---------------|----------------------------------|-------------------------------------|
| `POST`   | `/books`      | `201 Created` with the new book  | `400` validation or bad JSON        |
| `GET`    | `/books`      | `200 OK` with an array of books  |                                     |
| `GET`    | `/books/{id}` | `200 OK` with the book           | `400` bad id, `404` not found       |
| `PUT`    | `/books/{id}` | `200 OK` with the updated book   | `400` bad id or validation, `404`   |
| `DELETE` | `/books/{id}` | `204 No Content`                 | `400` bad id, `404` not found       |
| `GET`    | `/health`     | `200 OK` with `{"status":"ok"}`  | `503` if the database is unreachable |

Any other method on a known path returns `405 Method Not Allowed` with an `Allow` header.
Unknown paths return `404`.

A book has these fields:

| Field    | Type    | Required | Notes                                                |
|----------|---------|----------|------------------------------------------------------|
| `id`     | integer | (server) | Assigned on create. Never reused after a delete.     |
| `title`  | string  | yes      | Trimmed. At most 500 characters.                     |
| `author` | string  | yes      | Trimmed. At most 300 characters.                     |
| `year`   | integer | no       | `0` or omitted means unknown. Otherwise 1 to next year. |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 with a valid check digit. Hyphens and spaces are removed when stored. |

### Examples

Create a book:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"978-0-441-47812-5"}'
```

```json
{"id":1,"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}
```

List books, optionally filtered by author. The match is exact and ignores case:

```sh
curl 'http://localhost:8080/books?author=ursula%20k.%20le%20guin'
```

Get, update, and delete:

```sh
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969}'
curl -X DELETE http://localhost:8080/books/1
```

A validation failure:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' -d '{"year":1969}'
```

```json
{"error":"validation failed","fields":{"author":"author is required","title":"title is required"}}
```

## Behaviour notes

- `PUT` replaces the whole book. Any field left out of the body is cleared, so send
  every field you want to keep.
- Request bodies are limited to 1 MiB. Unknown JSON fields are rejected, which catches
  typos such as `"Title"`.
- Two books may share an ISBN, since one ISBN can cover several copies.
- The author filter uses SQLite's `NOCASE` comparison, which folds ASCII letters only.

## Project layout

| File            | Contents                                                     |
|-----------------|--------------------------------------------------------------|
| `main.go`       | Flags, HTTP server setup, graceful shutdown                  |
| `server.go`     | Routes, handlers, JSON decoding, error responses             |
| `store.go`      | SQLite schema and queries                                    |
| `book.go`       | Book types, input normalization, ISBN validation             |
| `*_test.go`     | Unit tests for validation and the store, and HTTP tests for the API |
