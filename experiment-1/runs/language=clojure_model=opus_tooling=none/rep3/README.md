# Books REST API

A Clojure REST API for managing a book collection, backed by SQLite.

## Requirements

- Clojure CLI (`clojure` / `clj`) 1.11+
- Java 11+

## Run

```bash
clojure -M:run           # starts on port 3000, data stored in ./books.db
clojure -M:run 8080      # custom port
```

## Test

```bash
clojure -M:test
```

## Endpoints

| Method | Path           | Description                           |
| ------ | -------------- | ------------------------------------- |
| GET    | /health        | Health check                          |
| POST   | /books         | Create a book                         |
| GET    | /books         | List all books (optional `?author=`)  |
| GET    | /books/{id}    | Get a book by ID                      |
| PUT    | /books/{id}    | Update a book                         |
| DELETE | /books/{id}    | Delete a book                         |

### Book payload

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`title` and `author` are required.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl http://localhost:3000/books?author=Frank%20Herbert
```
