# Books API

A REST API for managing a book collection, written in TypeScript with Express 5 and
SQLite (Node's built-in `node:sqlite` module, so there is no native dependency to compile).

## Requirements

- Node.js 22.13 or later (for `node:sqlite`)

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start          # serves the compiled build on http://localhost:3000
```

Or, without a build step: `npm run dev`.

Configuration is through environment variables:

| Variable  | Default    | Purpose                                         |
|-----------|------------|-------------------------------------------------|
| `PORT`    | `3000`     | Port to listen on                               |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral) |

## Test

```bash
npm test           # integration tests against an in-memory database
npm run typecheck  # type-checks sources and tests
```

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn` (string)
are optional and are returned as `null` when absent.

| Method | Path          | Description                                  | Success | Errors   |
|--------|---------------|----------------------------------------------|---------|----------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      | 200     |          |
| POST   | `/books`      | Create a book                                | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters by exact author name (case-insensitive) | 200 | 400 |
| GET    | `/books/{id}` | Get one book                                 | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book (full body, same rules as POST) | 200   | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                                | 204     | 400, 404 |

Errors are JSON: `{"error": "..."}`, with a `details` array of messages for validation
failures. A non-numeric id returns 400; an id with no matching book returns 404.

### Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
