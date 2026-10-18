# Flow

```mermaid
sequenceDiagram
    Client->>HTTPServer: POST /books {title,author,year,isbn}
    HTTPServer->>BookAPI: handleRequest: (HTTPRequest)
    BookAPI->>Book: bookFromJSONObject:error:
    Book-->>BookAPI: Book (or 400 validation error)
    BookAPI->>BookStore: insertBook:error:
    BookStore->>SQLite: INSERT INTO books (...)
    SQLite-->>BookStore: last_insert_rowid
    BookStore-->>BookAPI: Book (bookId set)
    BookAPI-->>HTTPServer: 201 + Location: /books/{id} + JSON body
    HTTPServer-->>Client: HTTP/1.1 201 Created
```

A `POST /books` is parsed by `HTTPRequestCreate` into a path/query/body, routed by `BookAPI handleRequest:` which validates the JSON body through `Book bookFromJSONObject:error:` (title and author required and non-blank; year must be an integer 0–9999 if present; isbn optional). On success the book is persisted by `BookStore insertBook:` via a prepared SQLite statement, the generated row id is assigned, and a `201 Created` with a `Location` header and the JSON book is returned. Errors are mapped to HTTP status codes through a shared `BookErrorDomain` enum (validation→400, not-found→404, database→500). The routing layer is deliberately socket-independent, so tests drive `handleRequest:` directly as well as over a real loopback socket.
