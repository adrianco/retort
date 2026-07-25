# Book API REST Service

A REST API service for managing a book collection, implemented in C++ with SQLite and HTTP server.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- C++17 compatible compiler (g++ 7+, clang++ 5+)
- CMake 3.16+
- SQLite3
- libcurl (for HTTP client in tests)

## Building

```bash
mkdir build
cd build
cmake ..
make -j4
```

## Running

### Start the server

```bash
./book_api
```

The server starts on port 8080 by default.

### Run tests

```bash
cd build
./book_api_tests
```

## API Examples

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

### Filter by author

```bash
curl "http://localhost:8080/books?author=George+Orwell"
```

### Get a book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Updated Author","year":2024,"isbn":"1234567890"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Project Structure

```
├── include/
│   ├── book.hpp      # Book model and validation
│   ├── database.hpp  # Database interface
│   ├── handler.hpp   # Request handler interface
│   └── server.hpp    # HTTP server interface
├── src/
│   ├── main.cpp      # Main entry point
│   ├── server.cpp    # HTTP server implementation
│   ├── handler.cpp   # Request handler implementation
│   ├── database.cpp  # SQLite database implementation
│   └── model.cpp     # Book model implementation
├── tests/
│   ├── test_database.cpp    # Database tests
│   ├── test_database_main.cpp # Test entry point
│   └── test_server.cpp      # Server integration tests
├── CMakeLists.txt
└── README.md
```

## License

MIT License
