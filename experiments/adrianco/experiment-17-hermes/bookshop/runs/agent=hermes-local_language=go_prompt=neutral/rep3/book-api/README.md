# Book API REST Service

A simple REST API service for managing a book collection with the following features:

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Go 1.21 or higher
- SQLite embedded database

## Installation

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

The server will start on port 8080 by default, or on the port specified by the `PORT` environment variable.

## API Endpoints

### Health Check
```
GET /health
```
Returns a JSON response indicating the service is healthy.

### Create a Book
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

### List Books
```
GET /books
```
Optional query parameter:
- `author` - Filter books by author name

### Get a Book
```
GET /books/{id}
```

### Update a Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Book Title",
  "author": "Updated Author Name",
  "year": 2024,
  "isbn": "0987654321"
}
```

### Delete a Book
```
DELETE /books/{id}
```

## Testing

Run the tests with:
```bash
go test
```

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created in the working directory.
