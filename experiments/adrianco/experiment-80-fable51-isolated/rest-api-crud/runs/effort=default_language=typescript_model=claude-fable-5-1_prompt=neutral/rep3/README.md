# Books API

A REST API for managing a book collection, written in TypeScript with
[Express 5](https://expressjs.com/) and SQLite (Node's built-in `node:sqlite` module,
so there is no native dependency to compile).

## Requirements

- Node.js 22.13 or newer (24+ recommended; `node:sqlite` is built in)

## Setup

```bash
npm install
```

## Run

```bash
npm run build   # compile TypeScript to dist/
npm start       # run the compiled server
# or, without a build step:
npm run dev
```

Configuration via environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `PORT`    | `3000`     | Port to listen on                             |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for no file) |

## Test

```bash
npm test
```

The tests start the app on an ephemeral port with an in-memory database and
exercise every endpoint over HTTP.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn`
(string) are optional and are stored as `null` when omitted.

| Method | Path          | Description                              | Success | Errors     |
|--------|---------------|------------------------------------------|---------|------------|
| GET    | `/health`     | Health check                             | 200     |            |
| POST   | `/books`      | Create a book                            | 201     | 400        |
| GET    | `/books`      | List books; `?author=` filters by author (exact, case-insensitive) | 200 | 400 |
| GET    | `/books/{id}` | Get one book                             | 200     | 404        |
| PUT    | `/books/{id}` | Replace a book (full body, same rules as POST) | 200 | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404        |

Errors are JSON: `{ "error": "..." }`, with a `details` array of messages for
validation failures.

### Example

```bash
curl -X POST localhost:3000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```
