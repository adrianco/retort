# Books API

A REST API for managing a book collection, written in TypeScript with Express 5 and
SQLite (Node's built-in `node:sqlite` module, so there are no native dependencies to compile).

## Requirements

- Node.js 22.13 or newer (24+ recommended)

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

The server listens on port 3000. Configuration is via environment variables:

| Variable  | Default    | Description                                      |
|-----------|------------|--------------------------------------------------|
| `PORT`    | `3000`     | HTTP port                                        |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

## Test

```bash
npm test
```

This compiles the project and runs the integration tests with Node's built-in test runner.
Each test starts the app on a random port against an in-memory database.

## Endpoints

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     |          |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters       | 200     | 400      |
| GET    | `/books/{id}` | Get one book                         | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404      |

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

- `title` and `author` are required, non-empty strings.
- `year` (integer) and `isbn` (string) are optional and stored as `null` when omitted.
- `PUT` is a full replacement, so it takes the same body and validation as `POST`.
- The `author` filter is an exact, case-insensitive match.
- Errors are returned as JSON: `{ "error": "...", "details": ["..."] }`.

## Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Layout

- `src/app.ts` – Express routes
- `src/db.ts` – SQLite-backed store
- `src/validation.ts` – input validation
- `src/server.ts` – entry point
- `tests/api.test.ts` – integration tests
