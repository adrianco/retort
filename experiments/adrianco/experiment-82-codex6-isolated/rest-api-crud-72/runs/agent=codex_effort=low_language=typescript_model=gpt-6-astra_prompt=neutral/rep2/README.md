# Book collection API

TypeScript REST service using Express and SQLite via Node's built-in `node:sqlite` module. Requires Node.js 22.13 or newer and npm. Earlier Node 22 releases may print an experimental SQLite warning.

## Setup and run

```sh
npm ci
npm run build
npm start
```

The service listens on port 3000 and creates `books.sqlite` in the current directory. Configure with `PORT` and `DB_PATH` (the database's parent directory must exist):

```sh
PORT=8080 DB_PATH=./collection.sqlite npm start
```

Run the build and integration tests:

```sh
npm test
```

Tests exercise Express middleware with in-process Node HTTP requests, isolated in-memory databases, and a temporary file to verify persistence. They do not require a listening network port.

## API

All responses, including errors, are JSON. Send request bodies with `Content-Type: application/json`.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | 200, `{"status":"ok"}` after checking the database |
| POST | `/books` | 201, created book and `Location` header |
| GET | `/books` | 200, array ordered by ID; optional `?author=` exact, case-sensitive filter |
| GET | `/books/:id` | 200, book; 404 if missing |
| PUT | `/books/:id` | 200, replaced book; 404 if missing |
| DELETE | `/books/:id` | 200, `{"message":"Book deleted"}`; 404 if missing |

Books have a generated positive integer `id`, required nonblank string `title` and `author`, optional integer `year`, and optional nonblank string `isbn`. Strings are trimmed. Optional fields default to `null`; ISBN is stored as text without imposing a particular ISBN format or uniqueness. PUT replaces all editable fields, so title and author are required and omitted optional fields become null. Unknown fields are ignored.

Invalid input, malformed JSON, or invalid IDs return 400 with `{"error":"..."}`. Unknown routes return 404. JSON bodies larger than 100 KB return 413.

```sh
curl -i http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:3000/books?author=Frank%20Herbert'
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE http://localhost:3000/books/1
```

The server closes its database on SIGINT/SIGTERM. SQL values use bound parameters.
