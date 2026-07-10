# Book Collection API

A REST API service for managing a book collection with SQLite database backend.

## Features

- Create books (POST /books)
- List all books (GET /books) with author filtering
- Get a single book by ID (GET /books/{id})
- Update books (PUT /books/{id})
- Delete books (DELETE /books/{id})
- Health check endpoint (GET /health)

## Setup

1. Ensure Go 1.26+ is installed
2. Run `go mod init book-api` to initialize the module
3. Install dependencies with `go mod tidy`
4. Run the service with `go run main.go`

## API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Running Tests

Run tests with `go test ./...`