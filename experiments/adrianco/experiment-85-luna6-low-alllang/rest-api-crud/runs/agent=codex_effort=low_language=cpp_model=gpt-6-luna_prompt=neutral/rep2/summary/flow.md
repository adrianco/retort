# Flow

```mermaid
sequenceDiagram
    Client->>main.cpp: POST /books {json}
    main.cpp->>main.cpp: serve_client() parse HTTP, read Content-Length body
    main.cpp->>book_api.cpp: handle(HttpRequest)
    book_api.cpp->>book_api.cpp: JsonParser.parse() + book_input() validate
    book_api.cpp->>SQLite: INSERT INTO books(...)
    SQLite-->>book_api.cpp: last_insert_rowid
    book_api.cpp->>SQLite: SELECT ... WHERE id=?
    SQLite-->>book_api.cpp: row
    book_api.cpp-->>main.cpp: HttpResponse{201, book_json}
    main.cpp-->>Client: HTTP/1.1 201 Created {json}
```

A `POST /books` request is read off a blocking POSIX socket in `serve_client()`, which parses the request line and `Content-Length` before handing a method/path/body triple to `BookApi::handle()`. The handler parses the body with a hand-written recursive-descent JSON parser, rejects missing/blank `title` or `author` (400) and out-of-range `year`, then inserts via a prepared statement and re-selects the row to echo the persisted record as JSON (201). Notable: the JSON parser is bespoke (no third-party library), strings are bound with `SQLITE_TRANSIENT` so there is no injection surface, the `?author=` filter is exact-match only (SQL `=`, not `LIKE`), and the server is single-threaded/blocking (one client at a time, `Connection: close`). `handle()` is fully decoupled from the socket layer, which is what makes the in-process test possible.
