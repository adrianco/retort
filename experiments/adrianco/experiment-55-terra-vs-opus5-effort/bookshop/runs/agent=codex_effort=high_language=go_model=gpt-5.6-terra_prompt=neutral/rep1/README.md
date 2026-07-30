# Book Collection API

A Go REST API backed by SQLite for creating and managing books.

## Run

Requires Go 1.26+ and a C compiler (the SQLite driver uses CGO).

```sh
go mod download
go run .
```

The service listens on `http://localhost:8080` and stores data in `books.db` by default. Set `PORT` to use another port, or `DATABASE_PATH` to use another SQLite database file.

## Endpoints

- `GET /health`
- `POST /books`
- `GET /books?author=Author%20Name`
- `GET /books/{id}`
- `PUT /books/{id}`
- `DELETE /books/{id}`

Create or replace a book with JSON such as:

```json
{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}
```

`title` and `author` are required. Successful creates return `201`, reads and updates return `200`, deletes return `204`, and missing books return `404`.

## Test

```sh
go test ./...
```
