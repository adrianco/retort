# Book API REST Service

A REST API service for managing a book collection built with Go, Gorilla Mux, and SQLite.

## Features

- Create, read, update, and delete books
- Search books by author
- Health check endpoint
- SQLite-based storage
- Input validation
- JSON responses

## Installation

### Prerequisites

- Go 1.21 or higher
- SQLite3

### Setup

1. Clone this repository

2. Install dependencies:

```bash
go mod tidy
```

3. Build the application:

```bash
go build -o book-api
```

## Running the Application

### Start the server:

```bash
./book-api
```

The server will start on `http://localhost:8080`

### Using Docker (optional):

```bash
docker build -t book-api .
docker run -p 8080:8080 book-api
```

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{"status":"healthy"}
```

### Create Book

```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```

Response: `201 Created`

### List Books

```
GET /books
```

With author filter:
```
GET /books?author=Author+Name
```

Response: `200 OK`

### Get Book by ID

```
GET /books/{id}
```

Response: `200 OK`

### Update Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "0987654321"
}
```

Response: `200 OK`

### Delete Book

```
DELETE /books/{id}
```

Response: `204 No Content`

## Input Validation

- `title`: Required, minimum 1 character
- `author`: Required, minimum 1 character
- `year`: Optional integer
- `isbn`: Optional string

## Running Tests

```bash
go test -v ./...
```

## Project Structure

```
.
├── main.go          # Entry point and server setup
├── book.go          # Data models
├── database.go      # Database operations
├── handler.go       # HTTP handlers
├── validator.go     # Input validation
├── main_test.go     # Test suite
├── go.mod           # Dependencies
└── README.md
```

## License

MIT
