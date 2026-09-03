# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Requirements

- Go 1.16 or higher
- SQLite (included in SQLite3)

## Installation

```bash
# Clone the repository
git clone <repository-url>

# Change directory to the project
cd book-api

# Build the project
go build -o book-api main.go

# Run the application
./book-api
```

## API Endpoints

### Health Check
`GET /health`

Returns a health status of the service.

### Get All Books
`GET /books`

Get all books, optionally filtered by author.

Example:
```bash
curl http://localhost:8080/books
curl http://localhost:8080/books?author=Smith
```

### Get a Single Book
`GET /books/{id}`

Get a single book by ID.

Example:
```bash
curl http://localhost:8080/books/1
```

### Create a Book
`POST /books`

Create a new book with the provided details.

Example:
```bash
curl -X POST http://localhost:8080/books \
-H "Content-Type: application/json" \
-d '{"title":"The Great Gatsby", "author":"F. Scott Fitzgerald", "year":1925, "isbn":"978-0743273502"}'
```

### Update a Book
`PUT /books/{id}`

Update an existing book by ID.

Example:
```bash
curl -X PUT http://localhost:8080/books/1 \
-H "Content-Type: application/json" \
-d '{"title":"Updated Title", "author":"Updated Author", "year":2023, "isbn":"978-0743273502"}'
```

### Delete a Book
`DELETE /books/{id}`

Delete a book by ID.

Example:
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run the tests using:

```bash
go test -v
```

## Database

The application uses SQLite for persistence. The database file is stored in `books.db` in the working directory.

## License

MIT