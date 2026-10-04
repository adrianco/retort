# Book collection API

A TypeScript REST API using Node's built-in HTTP server and SQLite. Requires Node.js 22.13+ (Node 24+ recommended) and npm. No framework was specified in the task, so no external runtime dependencies are needed. Some Node versions display an experimental SQLite warning.

## Setup and run

```sh
npm install
npm run build
npm start
```

The API listens on `http://127.0.0.1:3000`. Set `PORT`, `HOST`, or `DB_PATH` to override the defaults. The default database is `books.sqlite` in the working directory; it is created automatically and persists across restarts. The parent directory of a custom database path must exist. SIGINT and SIGTERM close the server and database.

```sh
npm test
```

Tests compile TypeScript and exercise the API request handler with in-process request/response streams and isolated real SQLite databases (no listening port required), including persistence across restarts.

## Endpoints

| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200, `{"status":"ok"}` after a database probe |
| POST | `/books` | 201, created book and `Location` header |
| GET | `/books` | 200, array ordered by ID |
| GET | `/books?author=Ursula%20K.%20Le%20Guin` | 200, exact case-sensitive author matches |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, replaced book |
| DELETE | `/books/{id}` | 200, `{"deleted":true,"id":1}` |

POST and PUT require `Content-Type: application/json` and non-blank string `title` and `author`. Optional `year` must be a safe integer or null; optional `isbn` must be a non-blank string or null. Strings are trimmed. ISBN format/uniqueness is not enforced. PUT replaces all fields: omitted optional fields become null. Unknown body fields are ignored. IDs are generated positive integers.

Invalid input or malformed JSON returns 400, missing resources return 404, unsupported book methods return 405, unsupported body content types return 415, and bodies exceeding 64 KiB return 413. Errors are JSON objects with an `error` string.

```sh
curl -i http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968,"isbn":"9780547773742"}'
curl http://127.0.0.1:3000/books/1
```
