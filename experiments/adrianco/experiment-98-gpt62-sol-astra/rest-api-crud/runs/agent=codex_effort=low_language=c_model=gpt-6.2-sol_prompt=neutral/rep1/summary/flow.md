# Flow

```mermaid
sequenceDiagram
    Client->>books.c route(): POST /books {json}
    books.c route()->>books.c books(): dispatch (method=POST, id=0)
    books.c books()->>books.c read_body(): parse + validate JSON
    books.c books()->>SQLite: INSERT ... RETURNING id,title,author,year,isbn
    SQLite-->>books.c books(): row
    books.c books()->>books.c reply(): 201 + Location header
    books.c reply()-->>Client: 201 {json book}
```

A request enters `route()` (registered as libevent's generic callback), which
matches the path (`/health`, `/books`, `/books/{id}`) and method, parses any
query string, then calls `books()` with the DB handle and parsed id/filter.
`books()` selects a single parameterized SQL statement per method, validates the
JSON body for create/update (`required_text` enforces nonblank string
title/author; year must be a 32-bit int or null; isbn a string or null), binds
parameters, steps the statement, and serializes the result row(s) to JSON via
`book_row()`. Status codes are mapped explicitly (201 create, 200 read/update,
204 delete, 404 absent, 400 bad input, 405 bad method, 500 DB error). Notable:
SQL uses `RETURNING` to echo the persisted row; libevent's `evhttp_send_reply`
is `#define`-stubbed by the C test to run handlers in-process without a socket;
memory is managed explicitly (`json_object_put`, `evbuffer_free`,
`sqlite3_finalize`).
