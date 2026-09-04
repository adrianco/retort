# Book API REST Service

This is a Rust implementation of a REST API service for managing a book collection using Axum, SQLite, and Tokio.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Setup

1. Make sure you have Rust installed
2. Navigate to the project directory
3. Run `cargo build` to build the project
4. Run `cargo run` to start the server

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Running Tests

Run `cargo test` to execute the tests.