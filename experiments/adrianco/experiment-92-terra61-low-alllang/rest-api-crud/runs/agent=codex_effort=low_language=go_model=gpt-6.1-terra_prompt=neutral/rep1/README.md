# Book collection API

A Go REST service backed by SQLite. Requires Go 1.23 or newer.

```sh
go mod download
go run .
```

The service listens on `:8080` and stores data in `books.db` by default. Set `ADDR` (for example, `localhost:8081`) and `DB_PATH` to override these values. The database and its table are created on startup.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

- `POST /books` creates a book and returns it with its generated ID and a `Location` header (201).
- `GET /books` lists books in ID order; `author` filters by exact author name. An empty list is `[]`.
- `GET /books/{id}` returns a book (200).
- `PUT /books/{id}` replaces its fields and returns the updated book (200).
- `DELETE /books/{id}` deletes it (204, no response body).
- `GET /health` checks database connectivity (200, or 503 if unavailable).

Request bodies are JSON objects with `title`, `author`, `year` (integer), and `isbn` (string). Title and author must be nonblank; surrounding whitespace is trimmed. Year and ISBN default to `0` and an empty string when omitted. PUT uses the same fields as POST. Invalid input returns 400 and missing books return 404; errors are JSON objects with an `error` field.

Run tests with `go test ./...`.
