# Book Collection API

A REST API for managing a book collection, built with Clojure, Compojure/Ring, and SQLite.

## Prerequisites

- [Clojure CLI](https://clojure.org/guides/install_clojure) (version 1.11+)
- Java 11+

## Setup

No additional setup is required. Dependencies are downloaded automatically on first run.

## Running the server

```bash
clojure -M:run
```

The server starts on port **3000** by default. Override with the `PORT` environment variable:

```bash
PORT=8080 clojure -M:run
```

## Running tests

```bash
clojure -M:test
```

## API Reference

### Health check

```
GET /health
```

Response `200`:
```json
{"status": "ok"}
```

---

### Create a book

```
POST /books
Content-Type: application/json
```

Body fields:

| Field  | Type    | Required |
|--------|---------|----------|
| title  | string  | yes      |
| author | string  | yes      |
| year   | integer | no       |
| isbn   | string  | no       |

Response `201`:
```json
{"id": 1, "title": "Clojure for the Brave and True", "author": "Daniel Higginbotham", "year": 2015, "isbn": "978-1-59327-591-4"}
```

Response `400` (validation error):
```json
{"error": "title is required"}
```

---

### List all books

```
GET /books
GET /books?author=<substring>
```

Response `200`:
```json
[
  {"id": 1, "title": "...", "author": "...", "year": 2015, "isbn": "..."},
  ...
]
```

The optional `?author=` query parameter filters by a case-insensitive substring match on the author field.

---

### Get a single book

```
GET /books/:id
```

Response `200`:
```json
{"id": 1, "title": "...", "author": "...", "year": 2015, "isbn": "..."}
```

Response `404`:
```json
{"error": "Book not found"}
```

---

### Update a book

```
PUT /books/:id
Content-Type: application/json
```

Same body fields as POST. `title` and `author` are required.

Response `200`: updated book object  
Response `400`: validation error  
Response `404`: book not found

---

### Delete a book

```
DELETE /books/:id
```

Response `204`: no content  
Response `404`: book not found

## Data storage

Books are stored in a SQLite database file `books.db` in the working directory. The file is created automatically on first start.
