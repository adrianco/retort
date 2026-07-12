# Book API REST Service

A REST API service for managing a book collection built with Go, SQLite, and gorilla/mux.

## Features

- **Health Check**: `/health` - Returns API health status
- **Books CRUD**:
  - `POST /books` - Create a new book
  - `GET /books` - List all books (supports `?author=` filter)
  - `GET /books/{id}` - Get a single book by ID
  - `PUT /books/{id}` - Update a book
  - `DELETE /books/{id}` - Delete a book

## Requirements

- Go 1.21 or higher
- SQLite3 (system library)

## Installation

```bash
cd book-api
go mod tidy
go build -o book-api .
```

## Usage

### Running the Server

```bash
./book-api
```

The server starts on port 8080 by default. You can customize the port using the `PORT` environment variable:

```bash
PORT=3000 ./book-api
```

## API Endpoints

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

### List Books

```http
GET /books
```

With author filter:
```http
GET /books?author=John+Doe
```

### Get Book

```http
GET /books/1
```

### Create Book

```http
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Update Book

```http
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Delete Book

```http
DELETE /books/1
```

## Testing

Run tests with:

```bash
go test -v ./...
```

## Project Structure

```
book-api/
├── main.go         # Main application file
├── go.mod          # Go module definition
├── go.sum          # Go dependencies checksum
└── README.md       # This file
```
