# Books API

A REST API for managing a book collection, built with TypeScript, Express and
SQLite (Node's built-in `node:sqlite` module, so there are no native dependencies).

## Requirements

- Node.js 24+ (for the built-in `node:sqlite` module)

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

The server listens on port 3000 by default and stores data in `books.db`.
Override with the `PORT` and `DB_PATH` environment variables.

## Test

```bash
npm test
```

Tests run against an in-memory database on an ephemeral port.

## Endpoints

| Method | Path          | Description                                   | Success |
| ------ | ------------- | --------------------------------------------- | ------- |
| GET    | `/health`     | Health check                                  | 200     |
| POST   | `/books`      | Create a book                                 | 201     |
| GET    | `/books`      | List books (optional `?author=` exact filter) | 200     |
| GET    | `/books/{id}` | Get one book                                  | 200     |
| PUT    | `/books/{id}` | Replace a book                                | 200     |
| DELETE | `/books/{id}` | Delete a book                                 | 204     |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional).

Errors are JSON: `400` for validation failures or malformed JSON
(`{"error": "...", "details": [...]}`), `404` for unknown books.
`PUT` is a full replacement: omitted optional fields are set to `null`.

## Example

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```
