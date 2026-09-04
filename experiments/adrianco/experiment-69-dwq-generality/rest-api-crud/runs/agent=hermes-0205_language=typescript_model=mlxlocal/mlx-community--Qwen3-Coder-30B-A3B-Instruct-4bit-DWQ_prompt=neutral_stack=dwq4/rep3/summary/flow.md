# Flow

```mermaid
sequenceDiagram
    Client->>server.js: POST /books {title,author,year,isbn}
    server.js->>server.js: express.json() parse
    server.js->>server.js: validate title && author
    server.js->>books.db: prepare + run INSERT INTO books
    books.db-->>server.js: this.lastID
    server.js->>books.db: SELECT * FROM books WHERE id = ?
    books.db-->>server.js: row
    server.js-->>Client: 201 {id,title,author,year,isbn}
```

`POST /books` parses the JSON body, rejects a missing `title` or `author` with `400` before touching the database, then issues a parameterized `INSERT` through a per-request prepared statement and re-reads the row by `this.lastID` so the response carries the generated id. All five CRUD routes follow the same shape: validate, parameterized SQL via the `sqlite3` callback API, map errors to `500` and empty results to `404`.

Deviations from common patterns: the prepared statements created per request (`server.js:48`, `:127`, `:159`) are never `finalize()`d and the database handle is never closed; callbacks are nested rather than promisified; `PUT` requires a full body (no partial update); `:id` is passed to SQL unvalidated, so a non-numeric id yields `404` rather than `400`; the database path is a fixed relative `./books.db` with no environment override, so every process sharing a working directory shares state.
