# Books API

A small REST API for managing a book collection, written in TypeScript with Express and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 18 or newer
- npm

## Setup

```bash
npm install
```

## Run

Development (TypeScript via ts-node):

```bash
npm run dev
```

Production build and run:

```bash
npm run build
npm start
```

By default the server listens on port `3000` and stores data in `books.db` in the working directory. Override with environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_FILE` — SQLite database path (default `books.db`; use `:memory:` for an ephemeral DB)

## Test

```bash
npm test
```

Tests use an in-memory SQLite database, so no setup is required.

## Endpoints

| Method | Path           | Description                                  |
| ------ | -------------- | -------------------------------------------- |
| GET    | `/health`      | Health check, returns `{ "status": "ok" }`   |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List all books (filter with `?author=Name`)  |
| GET    | `/books/{id}`  | Get a single book by id                      |
| PUT    | `/books/{id}`  | Update a book                                |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book payload

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0345339683"
}
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional.

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid input
- `404 Not Found` — book id does not exist

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'
```
