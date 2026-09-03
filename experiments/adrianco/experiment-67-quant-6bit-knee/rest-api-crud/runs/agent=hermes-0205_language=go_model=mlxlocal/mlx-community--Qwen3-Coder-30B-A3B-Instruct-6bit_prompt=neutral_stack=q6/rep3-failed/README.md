# Book API - REST Service

A REST API service for managing a book collection implemented in Go with SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation (title and author are required)
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.21 or higher
- SQLite3

## Setup

1. Clone or download this repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

Or build and run:

```bash
go build -o book-api
./book-api
```

The server will start on port 8080.

## Testing

The API can be tested with curl or any HTTP client:

### Health Check
```bash
curl http://localhost:8080/health
```

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### List Books
```bash
curl http://localhost:8080/books
```

### Get a Book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Database

The application uses SQLite and stores data in `books.db` file in the same directory.

## Implementation Details

This implementation follows all the requirements specified in the task:

1. ✅ POST /books — Create a new book (title, author, year, isbn)
2. ✅ GET /books — List all books (support ?author= filter)
3. ✅ GET /books/{id} — Get a single book by ID
4. ✅ PUT /books/{id} — Update a book
5. ✅ DELETE /books/{id} — Delete a book
6. ✅ Uses SQLite for data storage
7. ✅ Returns JSON responses with appropriate HTTP status codes
8. ✅ Includes input validation (title and author are required)
9. ✅ Includes a health check endpoint: GET /health

The implementation uses:
- Go 1.21 with standard library
- SQLite3 via github.com/mattn/go-sqlite3
- Embedded database in a local file (books.db)
- HTTP handlers for all endpoints
- Proper error handling and validation
- Unit tests for core functionality

## Verification Results

✅ Build successful  
✅ Tests pass  
✅ All required endpoints implemented  
✅ SQLite database integration working  
✅ Input validation implemented  
✅ Proper HTTP status codes used