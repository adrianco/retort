# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Node.js (v14 or higher)
- npm (v6 or higher)

## Installation

1. Clone the repository or download the files
2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Development Mode
```bash
npm run dev
```

The API will be available at `http://localhost:3000`

## API Endpoints

### Health Check
`GET /health`

### Create Book
`POST /books`

Request body:
```json
{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```

### Get All Books
`GET /books`

Optional query parameter:
- `author`: Filter books by author name (partial match)

### Get Book by ID
`GET /books/{id}`

### Update Book
`PUT /books/{id}`

Request body:
```json
{
  "title": "Updated Book Title",
  "author": "Updated Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```

### Delete Book
`DELETE /books/{id}`

## Database

The application uses SQLite for data persistence. The database file `books.db` is created automatically in the project root.

## Testing

The application can be tested using curl commands or any HTTP client:

### Example curl commands:
```bash
# Health check
curl http://localhost:3000/health

# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'

# Get all books
curl http://localhost:3000/books

# Get books by author
curl http://localhost:3000/books?author=Fitzgerald

# Get a single book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby - Updated","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-6"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```

## License

MIT