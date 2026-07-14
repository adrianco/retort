# Book Collection API

A REST API service for managing a book collection, written in Go with SQLite storage.

## Requirements

- Go 1.21+

## Setup

```bash
go mod download
```

## Run

```bash
go run .
```

The server listens on port `8080` by default. The SQLite database is stored in `books.db` in the current directory.

## Build

```bash
go build -o bookapi .
./bookapi
```

## Test

```bash
go test ./...
```

## API Endpoints

### Health Check

```
GET /health
```

Response `200 OK`:
```json
{"status": "ok"}
```

### Create a Book

```
POST /books
Content-Type: application/json

{"title": "The Go Programming Language", "author": "Donovan", "year": 2015, "isbn": "978-0134190440"}
```

- `title` and `author` are required.
- `year` and `isbn` are optional.

Response `201 Created`:
```json
{"id": 1, "title": "The Go Programming Language", "author": "Donovan", "year": 2015, "isbn": "978-0134190440"}
```

### List Books

```
GET /books
GET /books?author=Donovan
```

Response `200 OK`:
```json
[
  {"id": 1, "title": "The Go Programming Language", "author": "Donovan", "year": 2015, "isbn": "978-0134190440"}
]
```

Use the optional `?author=` query parameter to filter by author name.

### Get a Book

```
GET /books/{id}
```

Response `200 OK` or `404 Not Found`.

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{"title": "Updated Title", "author": "Updated Author", "year": 2024}
```

- `title` and `author` are required.

Response `200 OK` or `404 Not Found`.

### Delete a Book

```
DELETE /books/{id}
```

Response `204 No Content` or `404 Not Found`.

## Example with curl

```bash
# Create
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965}' | jq .

# List
curl -s http://localhost:8080/books | jq .

# Filter by author
curl -s 'http://localhost:8080/books?author=Herbert' | jq .

# Get by ID
curl -s http://localhost:8080/books/1 | jq .

# Update
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}' | jq .

# Delete
curl -s -X DELETE http://localhost:8080/books/1
```
