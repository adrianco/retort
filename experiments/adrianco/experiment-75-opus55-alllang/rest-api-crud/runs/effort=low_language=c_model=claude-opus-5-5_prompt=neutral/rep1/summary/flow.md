# Flow

```mermaid
sequenceDiagram
    Client->>server.c: POST /books {json}
    server.c->>server.c: read request, parse Content-Length body
    server.c->>books.c: books_handle("POST","/books",body)
    books.c->>books.c: parse_book_json + validate(title,author)
    books.c->>SQLite: INSERT INTO books(...)
    SQLite-->>books.c: last_insert_rowid
    books.c->>SQLite: SELECT ... WHERE id=?
    SQLite-->>books.c: row
    books.c-->>server.c: response_t{201, json}
    server.c-->>Client: 201 Created {book}
```

A `POST /books` is read by `server.c:handle_client`, which reads until the full
Content-Length body has arrived, then dispatches to `books.c:books_handle`. The
router parses the flat JSON body, validates that `title` and `author` are present
non-blank strings (400 otherwise), inserts the row, then re-reads it by
`last_insert_rowid()` and returns it as `201`. Persistence is real SQLite (default
`books.db`, `:memory:` in tests). The server is single-threaded, one request per
connection (`Connection: close`), with no pagination on list. Input validation,
JSON string escaping, and `%`/`+` URL-decoding of the `?author=` filter are all
present.
