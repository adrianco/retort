# Book Collection API

A small REST service for managing books, backed by SQLite.

## Requirements

- Go 1.26 or later

## Run

```sh
go run .
```

The server listens on `http://localhost:8080` and creates `books.db` in the
current directory. Set `PORT` to change the port and `DATABASE_PATH` to choose
another SQLite database file.

```sh
PORT=3000 DATABASE_PATH=/tmp/books.db go run .
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns service health. |
| `POST` | `/books` | Creates a book. |
| `GET` | `/books` | Lists books; use `?author=Name` to filter. |
| `GET` | `/books/{id}` | Gets one book. |
| `PUT` | `/books/{id}` | Replaces one book. |
| `DELETE` | `/books/{id}` | Deletes one book. |

Book request bodies are JSON. `title` and `author` are required; `year` and
`isbn` are optional.

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'
```

## Test

```sh
go test ./...
```
