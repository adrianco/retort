# Book API REST Service

A REST API service for managing a book collection with SQLite database.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Go 1.26 or later
- SQLite database (embedded)

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

The server will start on port 8080 by default. You can override the port by setting the PORT environment variable:
```bash
PORT=9000 go run main.go
```

## API Endpoints

### Health Check
```
GET /health
```

### Create a Book
```
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### List Books
```
GET /books
```

To filter by author:
```
GET /books?author=Fitzgerald
```

### Get a Book by ID
```
GET /books/1
```

### Update a Book
```
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby - Revised Edition",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete a Book
```
DELETE /books/1
```

## Testing

The implementation has been manually tested and verified to work correctly with all endpoints. 
The following tests were performed:
- Health check endpoint returns healthy status
- POST /books creates a new book with proper validation
- GET /books lists all books correctly
- GET /books supports author filtering
- GET /books/{id} returns correct book by ID
- PUT /books/{id} updates a book
- DELETE /books/{id} deletes a book
- All endpoints return appropriate HTTP status codes
- Input validation works for required fields (title and author)

## Database

The application uses an SQLite database file called `books.db` in the project directory. The database is automatically created when the application starts.

## License

This project is licensed under the MIT License.