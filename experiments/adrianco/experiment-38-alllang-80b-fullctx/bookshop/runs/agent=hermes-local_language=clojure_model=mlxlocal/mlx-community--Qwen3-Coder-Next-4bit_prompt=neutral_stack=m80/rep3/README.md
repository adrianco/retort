# Book API REST Service

A REST API service for managing a book collection built with Clojure.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Java 11 or higher
- Clojure CLI (tools.deps)

## Setup

1. Clone or navigate to the project directory

2. Run tests:
   ```bash
   clojure -M:test
   ```

3. Run the server:
   ```bash
   clojure -M:run
   ```

The server will start on port 3000 and create a `books.db` SQLite database file.

## API Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl "http://localhost:3000/books?author=George%20Orwell"
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated)", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Project Structure

```
.
├── deps.edn          # Project dependencies
├── src/
│   └── book_api/
│       ├── core.clj  # Main entry point
│       ├── db.clj    # Database operations
│       └── routes.clj # API routes
├── test/
│   └── book_api/
│       ├── test_db.clj    # Database tests
│       ├── test_routes.clj # API route tests
│       └── test_all.clj   # Test runner
└── README.md
```

## License

MIT
