# Book API

A REST API service for managing a book collection built with Clojure.

## Features

- Create, read, update, and delete books
- Filter books by author
- SQLite database for persistent storage
- Input validation
- Health check endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /books | Create a new book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a single book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |
| GET | /health | Health check endpoint |

## Requirements

- Java 8 or higher
- Leiningen 2.0 or higher

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd book-api
```

## Usage

### Start the Server

```bash
lein run
```

The server will start on port 3000.

### Run Tests

```bash
lein test
```

### Build Uberjar

```bash
lein uberjar
```

The jar will be created in `target/uberjar/book-api-0.1.0-SNAPSHOT-standalone.jar`.

### Run Tests with Coverage

```bash
lein test :all
```

## Example API Requests

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

### List All Books

```bash
curl http://localhost:3000/books
```

### Filter by Author

```bash
curl "http://localhost:3000/books?author=George%20Orwell"
```

### Get a Single Book

```bash
curl http://localhost:3000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984 (Updated)",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "9780451524935"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health Check

```bash
curl http://localhost:3000/health
```

## Project Structure

```
book-api/
├── project.clj          # Project configuration
├── README.md            # This file
├── src/
│   └── book_api/
│       ├── core.clj     # Application entry point
│       ├── db.clj       # Database layer
│       ├── handlers.clj # Request handlers
│       ├── routes.clj   # API routes
│       └── schema.clj   # Data schema and validation
├── test/
│   └── book_api/
│       ├── db_test.clj       # Database tests
│       └── handlers_test.clj # Handler tests
└── resources/
    └── db.sql           # SQL queries for HugSQL
```

## License

MIT License
