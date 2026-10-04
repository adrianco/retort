# Books API

A REST API for managing a book collection, written in TypeScript with
[Express](https://expressjs.com/) and SQLite (Node's built-in `node:sqlite` module, so
there is no native dependency to compile).

## Requirements

- Node.js 22.13 or newer (for `node:sqlite`)

## Setup

```bash
npm install
```

## Run

```bash
npm run build   # compile TypeScript to dist/
npm start       # start the compiled server
```

Or run straight from source during development:

```bash
npm run dev
```

Configuration is via environment variables:

| Variable  | Default    | Description                                      |
| --------- | ---------- | ------------------------------------------------ |
| `PORT`    | `3000`     | Port to listen on                                |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

## Test

```bash
npm test          # integration tests against an in-memory database
npm run typecheck # type-check source and tests
```

## API

A book looks like this:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn`
(string) are optional and are returned as `null` when absent.

| Method | Path          | Description                                 | Success | Errors     |
| ------ | ------------- | ------------------------------------------- | ------- | ---------- |
| GET    | `/health`     | Health check                                | 200     |            |
| POST   | `/books`      | Create a book                               | 201     | 400        |
| GET    | `/books`      | List books; `?author=` filters by author    | 200     | 400        |
| GET    | `/books/{id}` | Get one book                                | 200     | 400, 404   |
| PUT    | `/books/{id}` | Replace a book (full body, same validation) | 200     | 400, 404   |
| DELETE | `/books/{id}` | Delete a book                               | 204     | 400, 404   |

The `author` filter is an exact, case-insensitive match. Errors are JSON:
`{ "error": "...", "details": ["..."] }` (`details` is present for validation failures).

### Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
