# Book collection API

Go REST service using the standard library's `net/http` and SQLite. Data persists in a local database file. No external database server is needed.

## Setup and run

Requires Go 1.22+ and a C compiler (SQLite driver uses CGO; on macOS install Xcode Command Line Tools, on Linux install GCC).

```sh
go mod download
go run .
```

The server listens on `:8080` and creates `books.db` in the current directory. Configure with environment variables:

```sh
ADDR=127.0.0.1:9090 DB_PATH=/path/to/books.db go run .
```

The database's parent directory must exist. To build and test:

```sh
go build -o books .
go test ./...
go test -race ./...
```

## API

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and Location header |
| GET | `/books` | 200, array of books ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact, case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 204, no body |
| GET | `/health` | 200, `{"status":"ok"}`; 503 if database unavailable |

Create or replace a book:

```sh
curl -i http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"updated"}'
curl -i -X DELETE http://localhost:8080/books/1
```

Book responses contain `id`, `title`, `author`, `year`, and `isbn`. IDs are server-generated positive integers. Title and author are required strings and are trimmed; whitespace-only values are rejected. Year is an optional integer (default 0), and ISBN is an optional string (default empty); no ISBN checksum or uniqueness restriction is imposed. PUT replaces all editable fields and requires title and author. Unknown input fields, malformed JSON, multiple JSON values, and bodies over 1 MiB are rejected with 400.

Errors are JSON objects such as `{"error":"book not found"}`. Invalid IDs/input return 400, missing books/routes return 404, unsupported methods return 405 with an Allow header, and database failures return 500. An empty list is `[]`. This service has no authentication; deploy behind an access-controlled proxy if needed.
