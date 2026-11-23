# Book Collection API

This Go service stores books in a local SQLite database. It requires Go 1.22 or newer.

## Setup and run

```sh
go mod download
go run .
```

The service listens on port 8080 and creates `books.db` in the working directory. Set `ADDR` to change the listening address or `BOOKS_DB` to change the SQLite file path.

## API

| Method | Path | Successful response |
| --- | --- | --- |
| GET | `/health` | `200 OK` with the database health status |
| POST | `/books` | `201 Created` with the book and a `Location` header |
| GET | `/books` | `200 OK` with an array of books |
| GET | `/books/{id}` | `200 OK` with the book |
| PUT | `/books/{id}` | `200 OK` with the replacement book |
| DELETE | `/books/{id}` | `204 No Content` |

Use `GET /books?author=Octavia+E.+Butler` for an exact, case-sensitive author match. Book IDs are positive integers assigned by the service. POST and PUT require nonblank `title` and `author` strings. The integer `year` and string `isbn` are optional and default to `0` and `""` when omitted. PUT replaces all book fields and preserves the ID.

Invalid input returns `400 Bad Request`. A valid ID with no matching book returns `404 Not Found`. Errors use a JSON object with an `error` field.

```sh
curl -i http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'
curl http://localhost:8080/health
```

## Tests

```sh
go test ./...
```
