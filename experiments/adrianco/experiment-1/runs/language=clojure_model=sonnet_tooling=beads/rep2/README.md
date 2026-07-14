# Books API

A REST API service for managing a book collection, built with Clojure, Ring/Compojure, and SQLite.

## Prerequisites

- [Clojure CLI](https://clojure.org/guides/install_clojure) (v1.11+)
- Java 11+

## Setup

Clone the repository and install dependencies (resolved automatically by Clojure CLI):

```bash
clojure -P
```

## Running the Server

```bash
clojure -M:run
```

The server starts on port **3000** by default. Set the `PORT` environment variable to override:

```bash
PORT=8080 clojure -M:run
```

## Running Tests

```bash
clojure -M:test
```

## API Reference

### Health Check

```
GET /health
```

Response:
```json
{"status": "ok"}
```

### List Books

```
GET /books
GET /books?author=Tolkien
```

Supports optional `?author=` query parameter to filter by author (substring match).

Response `200 OK`:
```json
[
  {"id": 1, "title": "The Hobbit", "author": "Tolkien", "year": 1937, "isbn": "...", "created_at": "..."}
]
```

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

- `title` and `author` are **required**
- `year` and `isbn` are optional

Response `201 Created`:
```json
{"id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0261102217"}
```

Response `400 Bad Request` (missing required fields):
```json
{"errors": ["title is required"]}
```

### Get a Book

```
GET /books/{id}
```

Response `200 OK` or `404 Not Found`.

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "978-0000000000"
}
```

- `title` and `author` are **required**

Response `200 OK` or `404 Not Found`.

### Delete a Book

```
DELETE /books/{id}
```

Response `204 No Content` or `404 Not Found`.

## Data Storage

Books are stored in a SQLite database file (`books.db`) created automatically in the working directory on first run.
