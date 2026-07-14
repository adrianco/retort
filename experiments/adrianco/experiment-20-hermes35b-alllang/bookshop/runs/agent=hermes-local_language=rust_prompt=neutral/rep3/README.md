# Book API

A minimal REST API for managing a book collection, built in Rust with `actix-web` and SQLite.

## Endpoints

| Method   | Endpoint            | Description              |
|----------|---------------------|--------------------------|
| `GET`    | `/health`           | Health check             |
| `POST`   | `/books`            | Create a new book        |
| `GET`    | `/books`            | List all books           |
| `GET`    | `/books/{id}`       | Get a book by ID         |
| `PUT`    | `/books/{id}`       | Update a book by ID      |
| `DELETE` | `/books/{id}`       | Delete a book by ID      |

### Query Parameters

- `GET /books?author=<name>` — Filter books by author

### Create Book Request Body (JSON)

```json
{
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1-7185-0044-4"
}
```

- `title` and `author` are required.
- `year` and `isbn` are optional.

### Update Book Request Body (JSON)

Any subset of the fields above is accepted — only provided fields are updated.

### Example Usage

```bash
# Create a book
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2019}'

# List all books
curl http://127.0.0.1:8080/books

# List books by author
curl "http://127.0.0.1:8080/books?author=Steve%20Klabnik"

# Get a single book
curl http://127.0.0.1:8080/books/1

# Update a book
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Rust Programming Language, 2nd Edition"}'

# Delete a book
curl -X DELETE http://127.0.0.1:8080/books/1
```

## Tech Stack

- **Rust** 2021 edition
- **actix-web** v4 (HTTP server)
- **rusqlite** v0.31 with `bundled` feature (SQLite database)
- **serde** / **serde_json** (serialization)

## Building and Running

```bash
cargo build --release
./target/release/book-api
```

The server starts on `http://127.0.0.1:8080`. The SQLite database is created automatically at `<temp>/book_api_dev.db`.

## Testing

```bash
cargo test
```

10 unit tests cover:
- Book creation and retrieval
- Partial and full updates
- Book deletion and deletion of nonexistent books
- Listing (empty and filtered by author)
- Database connection sharing via clone
- JSON serialization/deserialization
- Error response serialization
