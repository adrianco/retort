# Flow

```mermaid
sequenceDiagram
    Client->>main.cpp: POST /books {json}
    main.cpp->>main.cpp: serve() reads headers + body
    main.cpp->>book_api.cpp: handle("POST","/books",body)
    book_api.cpp->>book_api.cpp: validate(body) — title/author required
    book_api.cpp->>SQLite: INSERT INTO books(...)
    SQLite-->>book_api.cpp: last_insert_rowid
    book_api.cpp->>SQLite: SELECT ... WHERE id=?
    SQLite-->>book_api.cpp: row
    book_api.cpp-->>main.cpp: Response{201, book json}
    main.cpp-->>Client: HTTP/1.1 201 Created {json}
```

A `POST /books` request is read by `serve()`, which parses the request line and `Content-Length`, then hands `method/target/body` to `BookApi::handle`. Routing dispatches to `create()`, which validates the body with a hand-rolled JSON parser (title and author must be non-empty strings; year, if present, must be an integer), inserts via a prepared statement, then re-selects the new row to build the JSON response with status upgraded to 201. Parameterized SQL is used throughout, so no injection. The server is single-threaded, blocking, one connection at a time with `Connection: close`; there is no persistent connection reuse or concurrency.
