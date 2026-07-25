#!/bin/bash

# README for Book API REST Service

This is a REST API service for managing a book collection built with Objective-C.

## Features

- Create, read, update, and delete books
- SQLite database for persistent storage
- JSON responses
- Input validation
- Author filtering
- Health check endpoint

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /books | List all books (supports `?author=` filter) |
| POST | /books | Create a new book |
| GET | /books/{id} | Get a single book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

## Requirements

- clang compiler
- SQLite3 library
- json-c library (for JSON parsing)
- pthread library

## Installation

### On macOS (using Homebrew)

```bash
# Install dependencies
brew install sqlite json-c

# Clone and build
git clone <repository-url>
cd book-api
make
```

### On Ubuntu/Debian

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install clang libsqlite3-dev libjson-c-dev

# Build
make
```

### On other Linux distributions

Install the equivalent packages for your distribution:
- clang or gcc
- libsqlite3-dev
- libjson-c-dev (or libjson-c2 for older systems)

## Building

```bash
make
```

## Running

```bash
# Start the server
make run

# Or directly
./book-api
```

The server will start on port 8080.

## Testing

```bash
# Run integration tests
make test

# Or run tests directly
./run_tests.sh
```

## Usage Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=George%20Orwell"
```

### Get a specific book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Response Formats

### Success (200/201)

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Error (400/404/500)

```json
{
  "error": "Book not found"
}
```

### Health check

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Project Structure

```
.
├── Makefile           # Build configuration
├── main.m            # Entry point
├── server.h          # Server header
├── server.m          # HTTP server implementation
├── database.h        # Database header
├── database.m        # SQLite database layer
├── routes.h          # Routes header
├── routes.m          # API route handlers
├── utils.h           # Utility functions header
├── utils.m           # Utility functions
├── run_tests.sh      # Integration test script
└── README.md         # This file
```

## License

MIT License
