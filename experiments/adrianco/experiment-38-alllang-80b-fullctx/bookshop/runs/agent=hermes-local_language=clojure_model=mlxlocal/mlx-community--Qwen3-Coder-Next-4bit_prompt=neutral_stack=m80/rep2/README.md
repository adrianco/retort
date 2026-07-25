# Book API REST Service

A REST API service for managing a book collection built with Clojure.

## Features

- **Health Check**: `GET /health`
- **Books CRUD Operations**:
  - `POST /books` - Create a new book
  - `GET /books` - List all books (supports `?author=` filter)
  - `GET /books/{id}` - Get a single book by ID
  - `PUT /books/{id}` - Update a book
  - `DELETE /books/{id}` - Delete a book
- **SQLite Database**: Persistent data storage
- **Input Validation**: Title and author are required fields

## Setup

### Prerequisites

- Java 8 or higher
- Clojure CLI tools (or Leiningen)

### Building and Running

#### Using Leiningen

1. Clone this repository
2. Navigate to the project directory
3. Run the following commands:

```bash
# Build the project
lein ring uberwar

# Or run directly
lein ring server
```

#### Using lein run

```bash
lein run
```

The server will start on port 3000.

## API Endpoints

### Health Check

```bash
curl http://localhost:3000/health
```

Response:
```json
{"status":"healthy"}
```

### List All Books

```bash
curl http://localhost:3000/books
```

### Filter Books by Author

```bash
curl "http://localhost:3000/books?author=John Doe"
```

### Create a Book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }'
```

### Get a Book by ID

```bash
curl http://localhost:3000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby (Updated)",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3000/books/1
```

## Running Tests

```bash
lein test
```

## Project Structure

```
src/
└── book_api/
    ├── core.clj      # Main entry point
    ├── db.clj        # Database layer
    └── handler.clj   # HTTP handlers and routing
test/
└── book_api/
    ├── db_test.clj       # Database tests
    └── handler_test.clj  # API endpoint tests
```

## License

Copyright © 2024
