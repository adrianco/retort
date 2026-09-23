# Flow

```mermaid
sequenceDiagram
    Client->>main.c: POST /books {json}
    main.c->>main.c: read until Content-Length satisfied
    main.c->>books.c: books_handle(db, "POST", "/books", body)
    books.c->>books.c: parse_book() + blank() validation
    books.c->>SQLite: INSERT INTO books(...)
    SQLite-->>books.c: last_insert_rowid
    books.c->>SQLite: SELECT ... WHERE id=?
    SQLite-->>books.c: row
    books.c-->>main.c: response_t{201, json}
    main.c-->>Client: HTTP/1.1 201 Created {json}
```

`main.c:handle_conn` reads the whole request into a 1 MiB buffer, parses `Content-Length` to know when the body is complete, then calls the transport-independent `books.c:books_handle`. For POST it parses the flat JSON object with a hand-written parser, rejects blank `title`/`author` with 400, inserts via a prepared statement, and re-selects the new row to build the 201 response. The clean split between `main.c` (sockets) and `books.c` (logic) lets the tests drive `books_handle` directly against `:memory:` with no network. Notable: single-threaded blocking server, one connection at a time, `Connection: close` per request; the JSON parser is flat-only (rejects nested values) and silently ignores unknown keys.
