# Book collection API

TypeScript REST service using Express 5 and SQLite via Node's built-in `node:sqlite` module.
Requires Node.js 22.13+ and npm (SQLite may emit an experimental warning on Node 22).

## Setup and run

```sh
npm install
npm run build
npm start
```

The service listens on port 3000 and creates `books.sqlite` in the working directory.
Set `PORT` and `DATABASE_PATH` to override these defaults; the database's parent directory must exist.
Data survives service restarts. SIGINT/SIGTERM close the server and database.

```sh
PORT=8080 DATABASE_PATH=./collection.sqlite npm start
npm test
```

Tests compile the TypeScript and exercise the Express HTTP middleware stack with isolated SQLite databases (no listening ports needed),
including CRUD, author filtering, validation, error handling, health, and persistence.

## API

All responses are JSON. Book IDs are generated positive integers.

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book and `Location` header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Frank%20Herbert` | 200, exact, case-sensitive author match |
| GET | `/books/:id` | 200, book |
| PUT | `/books/:id` | 200, replaced book |
| DELETE | `/books/:id` | 200, `{"message":"Book deleted"}` |
| GET | `/health` | 200, `{"status":"ok"}` after a database check |

POST and PUT accept a JSON object with required nonblank string `title` and `author`.
Optional `year` must be a safe integer or null. Optional `isbn` must be a nonblank
string or null; ISBN checksums and uniqueness are not enforced. Strings are trimmed.
PUT replaces the book: omitted optional fields become null. Extra fields are ignored.

```sh
curl -i http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:3000/books?author=Frank%20Herbert'
```

Errors use `{"error":"message"}`: 400 for invalid input or IDs, 404 for missing books/routes,
413 for JSON bodies over 100 KB, and 500 for unexpected server errors.
