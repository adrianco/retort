# Book API

A REST API service for managing a book collection.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Node.js (v14 or later)
- npm

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the application:
   ```bash
   npm start
   ```

   Or for development with auto-restart:
   ```bash
   npm run dev
   ```

## API Endpoints

### Health Check
- **GET** `/health`

### Books Management
- **POST** `/books` - Create a new book
  - Required fields: `title`, `author`
  - Optional fields: `year`, `isbn`
  
- **GET** `/books` - List all books
  - Optional query parameter: `?author=Author Name` to filter by author
  
- **GET** `/books/:id` - Get a single book by ID
  
- **PUT** `/books/:id` - Update a book
  - Required fields: `title`, `author`
  - Optional fields: `year`, `isbn`
  
- **DELETE** `/books/:id` - Delete a book

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created in the project root.

## Testing

The API has been manually tested with curl commands. For automated testing, you can run:
```bash
npm test
```

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'

# Get all books
curl -X GET http://localhost:3000/books

# Get a specific book
curl -X GET http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Updated",
    "author": "F. Scott Fitzgerald",
    "year": 1926,
    "isbn": "978-0-7432-7356-6"
  }'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```

## License

This project is licensed under the MIT License.