# Book Collection API

A small REST API for managing a book collection, written in TypeScript with
[Express](https://expressjs.com/) and the Node.js built-in `node:sqlite` module
(no native compilation required).

## Requirements

- Node.js 22.5 or newer (uses the built-in `node:sqlite` module)
- npm

## Setup

```bash
npm install
```

## Run

```bash
npm run build      # compile TypeScript to dist/
npm start          # start on http://localhost:3000
```

For development without a build step:

```bash
npm run dev
```

Environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `PORT`    | `3000`     | HTTP port                                     |
| `DB_PATH` | `books.db` | SQLite file path (use `:memory:` for no file) |

## Test

```bash
npm test
```

## Endpoints

| Method | Path                    | Description                                  |
|--------|-------------------------|----------------------------------------------|
| GET    | `/health`               | Health check, returns `{"status":"ok"}`      |
| POST   | `/books`                | Create a book. Returns 201 with the book     |
| GET    | `/books`                | List books. Optional `?author=` exact filter |
| GET    | `/books/{id}`           | Get a book. 404 if missing                   |
| PUT    | `/books/{id}`           | Replace a book. 400 invalid, 404 missing     |
| DELETE | `/books/{id}`           | Delete a book. 204 on success, 404 missing   |

Book shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` is an optional
integer (0 to 9999). `isbn` is an optional 10 to 13 digit string, hyphens
allowed. Validation failures return 400 with an `errors` array.

Example:

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
