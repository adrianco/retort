# Book API

A REST API service for managing a book collection.

## Setup

1. Install Go (1.21 or later)
2. Install project dependencies:
   ```sh
   go mod tidy
   ```

## Run

```sh
go run main.go
```

The API will be available at `http://localhost:8080`

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Example Requests

### Create a book
```sh
curl -X POST -H "Content-Type: application/json" -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}' http://localhost:8080/books
```

### List books
```sh
curl http://localhost:8080/books
```

### Get a book by ID
```sh
curl http://localhost:8080/books/1
```

### Update a book
```sh
curl -X PUT -H "Content-Type: application/json" -d '{"title":"Animal Farm","author":"George Orwell","year":1945,"isbn":"9780451526342"}' http://localhost:8080/books/1
```

### Delete a book
```sh
curl -X DELETE http://localhost:8080/books/1
```

## Tests

Run tests with:
```sh
go test ./...
```
