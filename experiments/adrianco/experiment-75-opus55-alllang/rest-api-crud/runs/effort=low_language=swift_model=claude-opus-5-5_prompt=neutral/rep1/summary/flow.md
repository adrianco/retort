# Flow

```mermaid
sequenceDiagram
    Client->>HTTPServer: POST /books {json}
    HTTPServer->>HTTPServer: parse(headers + Content-Length body)
    HTTPServer->>Router: handle(HTTPRequest)
    Router->>Router: validate(body) — title/author required
    Router->>BookStore: create(Book)
    BookStore->>SQLite: INSERT ... (locked)
    SQLite-->>BookStore: last_insert_rowid
    BookStore-->>Router: Book(id: ...)
    Router-->>HTTPServer: 201 {json}
    HTTPServer-->>Client: HTTP/1.1 201 Created
```

A `POST /books` is buffered by `HTTPServer.receive` until headers and the full `Content-Length` body arrive, parsed into an `HTTPRequest`, and dispatched to `Router.handle`. The router decodes the JSON body into `BookInput`, trims and validates that `title` and `author` are non-empty (else 400), then calls `BookStore.create`, which inserts under an `NSLock` and returns the row id. The result is JSON-encoded (sorted keys) and returned as 201. The server is one-request-per-connection (`Connection: close`); all store access is serialized by a single lock. No pagination; author filter is exact-match (case-insensitive). Errors surface as JSON `{"error":...}` bodies with mapped status codes.
