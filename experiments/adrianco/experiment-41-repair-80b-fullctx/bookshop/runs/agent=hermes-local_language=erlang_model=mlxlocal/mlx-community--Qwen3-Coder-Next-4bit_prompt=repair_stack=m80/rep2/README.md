# Book API REST Service

A REST API service for managing a book collection written in Erlang.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Erlang/OTP 24+ 
- rebar3 (build tool)

## Setup

1. Clone or copy this repository to your workspace

2. Build the project using rebar3:

```bash
rebar3 compile
```

3. Run tests:

```bash
rebar3 eunit
```

## Running the Application

### Start the application:

```bash
rebar3 shell
```

Or run directly:

```bash
rebar3 run
```

The server will start on port 8080.

### API Usage Examples

#### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{"status":"ok"}
```

#### Create a Book (POST /books)

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

Response (201 Created):
```json
{"id":1,"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}
```

#### List All Books (GET /books)

```bash
curl http://localhost:8080/books
```

Response:
```json
{"books":[...]}
```

#### Filter by Author

```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

#### Get a Single Book (GET /books/{id})

```bash
curl http://localhost:8080/books/1
```

#### Update a Book (PUT /books/{id})

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)","year":1926}'
```

#### Delete a Book (DELETE /books/{id})

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Project Structure

```
.
├── rebar.config        # Project dependencies and configuration
├── src/
│   ├── book_api.erl           # Main application entry point
│   ├── book_api_app.erl       # Application callback module
│   ├── book_api_sup.erl       # Supervisor module
│   ├── book_api_handler.erl   # REST API handlers
│   ├── book_api_db.erl        # SQLite database module
│   └── book.erl               # Book model and validation
├── test/
│   ├── book_api_test.erl           # Unit tests
│   └── book_api_integration_test.erl # Integration tests
└── README.md
```

## Error Handling

The API returns appropriate HTTP status codes:

- 200 OK - Successful GET/PUT requests
- 201 Created - Successful POST request
- 204 No Content - Successful DELETE request
- 400 Bad Request - Invalid input data
- 404 Not Found - Resource not found

Error responses are returned as JSON:
```json
{"error":"error message"}
```
