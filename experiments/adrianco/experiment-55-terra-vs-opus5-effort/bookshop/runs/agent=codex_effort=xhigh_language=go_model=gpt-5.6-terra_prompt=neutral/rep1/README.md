# Book Collection API

A small REST API written in Go with SQLite storage.

## Run

Go 1.26+ and a C compiler are required (the SQLite driver uses CGO).

```sh
go mod download
go run .
```

The service listens on `http://localhost:8080`. Set `ADDR` to change the listen
address and `DATABASE_PATH` to change the SQLite file path (default: `books.db`).

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health status |
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List books; optionally use `?author=Name` |
| `GET` | `/books/{id}` | Fetch one book |
| `PUT` | `/books/{id}` | Replace a book |
| `DELETE` | `/books/{id}` | Delete a book |

Create or update requests accept JSON such as:

```json
{
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "9780441478125"
}
```

`title` and `author` are required. Successful creates return `201`, reads and
updates return `200`, and successful deletes return `204`. Errors are JSON in the
form `{"error":"..."}`.

## Test and build

```sh
go test ./...
go build ./...
```
