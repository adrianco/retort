# Flow

```mermaid
sequenceDiagram
    Client->>server.c: POST /books {json}
    server.c->>server.c: serve() reads request, frames headers+body
    server.c->>books.c: books_handle(db, "POST", "/books", query, body)
    books.c->>books.c: parse_book(body) + validate()
    books.c->>SQLite: INSERT INTO books(...)
    SQLite-->>books.c: last_insert_rowid
    books.c->>SQLite: SELECT ... WHERE id=?
    SQLite-->>books.c: row
    books.c-->>server.c: response_t{201, json body}
    server.c-->>Client: HTTP/1.1 201 Created {json}
```

A request to `POST /books` is read by `server.c:serve()`, which frames the HTTP
headers and body (enforcing a 1 MiB request cap and Content-Length). It calls
`books_handle`, which parses the flat-JSON body with a hand-written parser,
validates that `title` and `author` are non-empty strings (rejecting wrong types
and out-of-range `year`), inserts into SQLite via a prepared statement, then
re-selects the created row to return it as JSON with status 201. The server is a
single-threaded, sequential accept loop (one connection at a time); it has no
concurrency, no keep-alive (Connection: close), and no auth. JSON output escapes
control chars and encodes `\uXXXX`; the parser handles strings, integers, null,
and bool but not nested objects/arrays.
