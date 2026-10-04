# Books API

A REST service for managing a book collection, written in TypeScript on Node.js.
It uses only the Node standard library: `node:http` for the server and `node:sqlite`
for storage, so there are no runtime dependencies.

## Requirements

- Node.js 22.18 or newer (developed on Node 26)

## Setup

```bash
npm install
```

## Run

```bash
npm run build   # compile to dist/
npm start       # run the compiled server
```

Or run the TypeScript sources directly during development:

```bash
npm run dev
```

Configuration is by environment variable:

| Variable  | Default    | Purpose                                          |
| --------- | ---------- | ------------------------------------------------ |
| `PORT`    | `3000`     | Port to listen on                                |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

## Test

```bash
npm test            # integration tests against an in-memory database
npm run typecheck   # type-check sources and tests
```

## API

All request and response bodies are JSON. A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

| Method | Path          | Description                          | Success | Errors        |
| ------ | ------------- | ------------------------------------ | ------- | ------------- |
| GET    | `/health`     | Health check                         | 200     |               |
| POST   | `/books`      | Create a book                        | 201     | 400, 413      |
| GET    | `/books`      | List books, optional `?author=`      | 200     |               |
| GET    | `/books/{id}` | Get one book                         | 200     | 400, 404      |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404, 413 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 400, 404      |

Validation rules:

- `title` and `author` are required, non-empty strings.
- `year` is optional and must be an integer.
- `isbn` is optional and must be a non-empty string.
- `PUT` replaces the whole book, so omitted optional fields become `null`.
- The `?author=` filter matches the full author name, case-insensitively.

Errors have the shape `{ "error": "message" }`, with a `details` array listing
each problem when validation fails.

### Example

```bash
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X DELETE localhost:3000/books/1
```

## Layout

- `src/server.ts` — entry point
- `src/app.ts` — HTTP routing and error handling
- `src/store.ts` — SQLite storage
- `src/validation.ts` — input validation
- `tests/api.test.ts` — integration tests
