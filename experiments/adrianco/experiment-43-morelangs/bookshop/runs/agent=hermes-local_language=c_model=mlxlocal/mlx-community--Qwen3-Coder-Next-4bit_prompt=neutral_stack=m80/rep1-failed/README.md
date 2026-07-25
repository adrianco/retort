# Book API REST Service

A REST API service for managing a book collection implemented in C.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- GCC compiler
- libcurl development library
- SQLite3 development library
- pthread library

## Installation

On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install build-essential libcurl4-openssl-dev libsqlite3-dev
```

On macOS:
```bash
brew install curl sqlite
```

## Building

```bash
make
```

Or manually:
```bash
gcc -Wall -Wextra -g -o book-api main.c http.c db.c -lcurl -lsqlite3
```

## Running

```bash
./book-api
```

Options:
- `--db PATH` - Database path (default: books.db)
- `--port PORT` - Port to listen on (default: 8080)
- `--help` - Show help message

Example:
```bash
./book-api --port 3000 --db mylibrary.db
```

The server will start on port 8080 (or the specified port) and listen for incoming requests.

## API Usage

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{"status":"healthy","timestamp":1721668800}
```

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

Response (201 Created):
```json
{"id":1,"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}
```

### List All Books

```bash
curl http://localhost:8080/books
```

Response:
```json
{"books":[{"id":1,"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}],"count":1}
```

### Filter Books by Author

```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a Single Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated Edition)"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run the integration tests:

```bash
./run_tests.sh
```

Or manually test with:

```bash
# Start server in background
./book-api &
SERVER_PID=$!

# Wait for server to start
sleep 1

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Book","author":"Test Author","year":2024,"isbn":"123-456"}'

# List books
curl http://localhost:8080/books

# Health check
curl http://localhost:8080/health

# Stop server
kill $SERVER_PID
```

## Project Structure

```
.
├── Makefile          # Build configuration
├── README.md         # This file
├── main.c            # HTTP server implementation
├── http.c            # HTTP request/response handling
├── http.h            # HTTP module header
├── db.c              # SQLite database operations
├── db.h              # Database module header
├── run_tests.sh      # Test script
├── books.db          # SQLite database (created at runtime)
└── test_book_api.sh  # Integration tests
```

## License

MIT License
