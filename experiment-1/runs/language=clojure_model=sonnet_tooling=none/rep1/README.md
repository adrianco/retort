# Books API

A REST API service for managing a book collection, built with Clojure.

## Stack

- **Language**: Clojure 1.11
- **HTTP**: Ring + Compojure
- **Database**: SQLite via next.jdbc
- **JSON**: Cheshire

## Prerequisites

- Java 11+
- [Clojure CLI](https://clojure.org/guides/install_clojure) (`clojure` / `clj`)

## Running the server

```bash
clojure -M:run
```

The server starts on port 3000 by default. Set the `PORT` environment variable to change it:

```bash
PORT=8080 clojure -M:run
```

## Running tests

```bash
clojure -M:test
```

## API Endpoints

### Health check

```
GET /health
```

Response: `{"status":"ok"}`

### Create a book

```
POST /books
Content-Type: application/json

{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "978-0132350884"}
```

- `title` and `author` are required; `year` and `isbn` are optional
- Returns `201 Created` with the created book

### List all books

```
GET /books
GET /books?author=Martin   (filter by author, case-insensitive substring match)
```

Returns `200 OK` with an array of books.

### Get a book

```
GET /books/:id
```

Returns `200 OK` with the book, or `404 Not Found`.

### Update a book

```
PUT /books/:id
Content-Type: application/json

{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "978-0132350884"}
```

- `title` and `author` are required
- Returns `200 OK` with the updated book, or `404 Not Found`

### Delete a book

```
DELETE /books/:id
```

Returns `200 OK` on success, or `404 Not Found`.

## Data storage

SQLite database is stored as `books.db` in the working directory (created automatically on first run).
