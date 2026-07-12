# Book API

A REST API service for managing a book collection.

## Setup

1. Install Rust: https://www.rust-lang.org/tools/install

2. Clone the repository:
```bash
git clone <repository-url>
cd book_api
```

3. Set up the database:
```bash
cp .env.example .env
```

4. Run migrations:
```bash
diesel migration run
```

## Run

Start the server:
```bash
cargo run
```

The API will be available at http://127.0.0.1:8080

## API Endpoints

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (supports ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check

## Testing

Run tests:
```bash
cargo test
```

## Example Requests

Create a book:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"title": "1984", "author": "George Orwell"}' http://127.0.0.1:8080/books
```

List books:
```bash
curl http://127.0.0.1:8080/books
```

List books by author:
```bash
curl "http://127.0.0.1:8080/books?author=George%20Orwell"
```

Get a book by ID:
```bash
curl http://127.0.0.1:8080/books/<id>
```

Update a book:
```bash
curl -X PUT -H "Content-Type: application/json" -d '{"title": "Animal Farm"}' http://127.0.0.1:8080/books/<id>
```

Delete a book:
```bash
curl -X DELETE http://127.0.0.1:8080/books/<id>
```
