# Book Collection REST API

A REST API service for managing a book collection built with TypeScript and Bun.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (support ?author= filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Requirements

- Node.js (v18+ recommended)
- Bun (for running the application)

## Setup

1. Install dependencies:
```bash
bun install
```

2. Start the server:
```bash
bun run server.ts
```

3. The server will be available at http://localhost:3000

## API Endpoints

### Health Check
- **GET** `/health`

### Books Management
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books
- **GET** `/books/{id}` - Get a book by ID
- **PUT** `/books/{id}` - Update a book
- **DELETE** `/books/{id}` - Delete a book

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl "http://localhost:3000/books?author=Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:3000/books/{id}
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Revised Edition",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/{id}
```

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created automatically in the project root.

## Testing

Run the tests using:
```bash
bun test
```

## Implementation Details

### Technologies Used
- TypeScript with Bun runtime
- SQLite embedded database
- REST API with JSON responses
- Input validation for required fields

### Validation Rules
- Title and author are required fields
- Year must be a valid year between 1000 and 2100, or null
- All endpoints return appropriate HTTP status codes

### Data Model
```typescript
interface Book {
  id: string;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}
```

## Error Handling

- **400 Bad Request** - Invalid JSON or validation errors
- **404 Not Found** - Book not found for GET/PUT/DELETE operations
- **501 Not Implemented** - Not yet implemented endpoints (if any)

The API follows REST conventions and returns JSON responses for all operations.