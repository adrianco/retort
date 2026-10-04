# Book collection API

A Go REST service using `net/http` and persistent SQLite storage. The SQLite driver is pure Go; no C compiler or separate database server is required.

## Run

Requires Go 1.22 or later.

```sh
go mod download
go run .
```

The service listens on `:8080` and creates `books.db` in the current directory. Configure these with `ADDR` and `DB_PATH`:

```sh
ADDR=127.0.0.1:9000 DB_PATH=collection.db go run .
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

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780593098233"}'
curl -i -X DELETE http://localhost:8080/books/1
```

Books contain a server-generated integer `id`, `title`, `author`, integer `year`, and string `isbn`. Title and author are trimmed and required on both POST and PUT. Year and ISBN are optional and default to 0 and the empty string; PUT replaces all writable fields. ISBN is stored as supplied, with no uniqueness or format constraint. Empty lists return `[]`.

Errors use `{"error":"message"}`: invalid JSON, unknown fields, missing required fields, or invalid IDs return 400; missing books/routes return 404; unsupported methods return 405 with an Allow header. Bodies are limited to 1 MiB (413). Database errors return 500. All response bodies are JSON; DELETE success has no body.

## Build and test

```sh
go build -o bookcollection .
go test ./...
go test -race ./...
```

Integration tests use isolated temporary SQLite files and cover CRUD, author filtering, validation, routing, health checks, and persistence after reopening the database.
