# Books API

A small REST API for managing a book collection. Written in TypeScript using
Express and SQLite (`better-sqlite3`).

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

The server listens on `PORT` (default `3000`) and persists data to the file
referenced by `DB_PATH` (default `books.db`).

For development without a build step:

```bash
npm run dev
```

## Test

```bash
npm test
```

Tests use an in-memory SQLite database, so they leave no artifacts on disk.

## Endpoints

| Method | Path           | Description                       |
| ------ | -------------- | --------------------------------- |
| GET    | `/health`      | Health check                      |
| POST   | `/books`       | Create a book                     |
| GET    | `/books`       | List books (optional `?author=`)  |
| GET    | `/books/{id}`  | Get a book by id                  |
| PUT    | `/books/{id}`  | Update a book                     |
| DELETE | `/books/{id}`  | Delete a book                     |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required strings. `year` is an optional integer and
`isbn` is an optional string.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:3000/books?author=Frank%20Herbert
```
