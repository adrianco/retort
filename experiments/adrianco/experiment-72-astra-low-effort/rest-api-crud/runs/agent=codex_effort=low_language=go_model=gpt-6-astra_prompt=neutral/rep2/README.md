# Book collection API

A Go REST service using `net/http` and a persistent SQLite database. No framework was specified in the task, so routing uses the standard library.

## Setup and run

Requires Go 1.22 or later and a C compiler (the `github.com/mattn/go-sqlite3` driver uses CGO). On macOS, install Xcode command line tools; on Linux, install GCC or Clang.

```sh
go mod download
go run . -addr :8080 -db books.db
```

The database and schema are created automatically. Use a writable database path; its parent directory must exist. The default address is `:8080` and default database is `books.db`. Stop with Ctrl-C for graceful shutdown.

```sh
go build -o book-api .
./book-api -addr 127.0.0.1:8080 -db books.db
go test ./...
go test -race ./...
```

## API

| Method | Endpoint | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and `Location` header |
| GET | `/books` | 200, array ordered by ID (empty collection is `[]`) |
| GET | `/books?author=Frank%20Herbert` | 200, exact case-sensitive author match |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 204, no body |
| GET | `/health` | 200, `{"status":"ok"}`; 503 if database is unavailable |

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books/1
curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780593098233"}'
curl -i -X DELETE http://localhost:8080/books/1
curl http://localhost:8080/health
```

Books have a server-generated integer `id`, string `title`, string `author`, integer `year`, and string `isbn`. Title and author are required and trimmed; whitespace-only values are rejected. Year and ISBN are optional, defaulting to `0` and `""`. PUT replaces all editable fields, so omitted optional fields reset to defaults. No ISBN uniqueness or format restriction is imposed.

Bodies must contain one JSON object, at most 1 MiB, with no unknown fields. Invalid input or IDs return 400; missing books/routes return 404; unsupported methods return 405 with an `Allow` header. Database failures return 500. All responses except the bodyless 204 are JSON; errors have the form `{"error":"message"}`.

Tests cover the CRUD lifecycle, filtering, malformed and invalid input, routing, database health, and persistence across database reopen.
