# Book Collection API

A TypeScript REST API using Node's HTTP server and built-in SQLite. Requires Node.js 24 or newer and npm; no runtime dependencies or external database server are needed.

```sh
npm install
npm run build
npm start
```

The server defaults to `http://127.0.0.1:3000`. Set `PORT`, `HOST`, and `DB_PATH` to override the port, bind address, and database file. The default database is `books.sqlite` in the working directory and is created automatically. The database's parent directory must exist. SIGINT/SIGTERM close the server and database.

```sh
npm test
```

Tests compile the project and exercise the HTTP request handler in process with isolated SQLite databases (no listening socket required), including persistence across restarts.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | 200, `{"status":"ok"}` after a database query |
| POST | `/books` | 201, created book with generated integer `id`; `Location` header |
| GET | `/books` | 200, array ordered by ID; optional `?author=` exact, case-sensitive filter |
| GET | `/books/{id}` | 200, book; 404 if absent |
| PUT | `/books/{id}` | 200, replacement book; 404 if absent |
| DELETE | `/books/{id}` | 204, empty body; 404 if absent |

POST and PUT require `Content-Type: application/json` and an object containing non-empty string `title` and `author`. Whitespace is trimmed. Optional `year` is a safe integer or null; optional `isbn` is a non-empty string or null (no ISBN checksum enforcement). PUT replaces all fields: omitted year/isbn become null. Unknown fields are ignored. IDs must be positive safe integers.

Malformed JSON and invalid fields/IDs return 400, unsupported content types return 415, bodies over 1 MiB return 413, and unsupported book methods return 405 with `Allow`. Errors are JSON objects of the form `{"error":"message"}`. DELETE success has no body, as required by HTTP 204.

```sh
curl -i http://127.0.0.1:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968,"isbn":"9780547773742"}'
curl 'http://127.0.0.1:3000/books?author=Ursula%20K.%20Le%20Guin'
```
