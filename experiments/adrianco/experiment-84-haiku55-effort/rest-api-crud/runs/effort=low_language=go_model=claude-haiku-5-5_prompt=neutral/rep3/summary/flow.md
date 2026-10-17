# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {title,author,year,isbn}
    server.go->>server.go: decodeBook (MaxBytes, DisallowUnknownFields)
    server.go->>server.go: validateBook (title/author required, year 0..9999)
    server.go->>store.go: Store.Create(ctx, book)
    store.go->>store.go: INSERT INTO books ...
    store.go-->>server.go: Book{ID}
    server.go-->>Client: 201 + Location: /books/{id} + {json}
```

A `POST /books` request is size-limited to 1 MiB and decoded with
`DisallowUnknownFields` plus a trailing-data check; the body is trimmed and
validated (title and author required, year bounded 0–9999) before an INSERT.
On success the handler sets a `Location` header and returns 201 with the created
book. Errors are returned as `{"error": msg}` JSON: 400 for bad input, 404 for
missing IDs, 500 for internal/DB errors (logged, not leaked), 503 for `/health`
when the DB is unreachable. All persistence is context-aware SQLite; no
in-memory shortcut.
