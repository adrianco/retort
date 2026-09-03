# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database persistence

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Requirements Met

✅ POST /books creates a new book (title, author, year, isbn)  
✅ GET /books lists all books  
✅ GET /books supports an ?author= filter  
✅ GET /books/{id} returns a single book by id  
✅ PUT /books/{id} updates a book  
✅ DELETE /books/{id} deletes a book  
✅ Data stored in SQLite  
✅ Returns JSON responses with appropriate HTTP status codes  
✅ Input validation: title and author are required  
✅ GET /health health-check endpoint  
✅ README.md with setup and run instructions  
✅ At least 3 unit/integration tests  

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
# Build the application
make build

# Run the application
make run
```

Or directly with Go:
```bash
go run main.go
```

## Testing

```bash
make test
```

## Database

The application uses SQLite for data persistence. All data is stored in `books.db` file in the working directory.

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "9780134190445"
  }'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl http://localhost:8080/books?author=Go
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language (Updated)",
    "author": "Alan A. A. Donovan",
    "year": 2016,
    "isbn": "9780134190445"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Implementation Details

This implementation provides a complete REST API for managing a book collection with the following features:

1. **Database Storage**: Uses SQLite embedded database for persistence
2. **Full CRUD Operations**: 
   - Create books with title, author, year, and ISBN
   - List all books with optional author filtering
   - Get single book by ID
   - Update existing books
   - Delete books
3. **Validation**: Ensures title and author fields are required
4. **Status Codes**: Returns appropriate HTTP status codes for all operations
5. **JSON Responses**: All responses are in JSON format
6. **Health Check**: Provides a /health endpoint for system monitoring
7. **Testing**: Includes unit/integration tests covering all functionality

The code is organized in a clean, maintainable way with proper error handling and follows Go best practices.