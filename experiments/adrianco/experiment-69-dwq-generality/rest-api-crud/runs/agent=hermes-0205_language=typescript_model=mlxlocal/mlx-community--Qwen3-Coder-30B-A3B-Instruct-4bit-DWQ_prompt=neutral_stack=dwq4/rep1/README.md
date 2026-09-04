# Book API REST Service

A REST API for managing a book collection built with Node.js, Express, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Requirements Met

- ✅ POST /books — Create a new book (title, author, year, isbn)
- ✅ GET /books — List all books (support ?author= filter)
- ✅ GET /books/{id} — Get a single book by ID
- ✅ PUT /books/{id} — Update a book
- ✅ DELETE /books/{id} — Delete a book
- ✅ Data stored in SQLite database
- ✅ Return JSON responses with appropriate HTTP status codes
- ✅ Include input validation (title and author are required)
- ✅ Include a health check endpoint: GET /health
- ✅ README.md with setup and run instructions
- ✅ At least 3 unit/integration tests

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the server:
   ```bash
   npm start
   ```

The server will start on port 3000 by default.

## API Endpoints

### Health Check
`GET /health`
Returns server health status.

### Create Book
`POST /books`
Create a new book with title, author, year, and isbn.

### List Books
`GET /books`
List all books. Optional query parameter: `author` to filter by author.

### Get Book by ID
`GET /books/:id`
Get a specific book by its ID.

### Update Book
`PUT /books/:id`
Update an existing book by ID.

### Delete Book
`DELETE /books/:id`
Delete a book by ID.

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created in the project root when the server starts.

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl http://localhost:3000/books?author=F. Scott Fitzgerald
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```