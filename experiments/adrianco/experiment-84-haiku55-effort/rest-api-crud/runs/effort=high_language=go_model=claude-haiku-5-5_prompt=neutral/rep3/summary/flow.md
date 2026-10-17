# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {json}
    server.go->>server.go: decodeJSON (DisallowUnknownFields, MaxBytes)
    server.go->>book.go: in.Clean().Validate()
    book.go-->>server.go: ok / ValidationError(400)
    server.go->>store.go: Create(ctx, in)
    store.go->>SQLite: INSERT + SELECT by id
    SQLite-->>store.go: row
    store.go-->>server.go: Book
    server.go-->>Client: 201 {json} + Location
```

A `POST /books` request has its body decoded with unknown-field rejection and a 1 MiB cap, then the input is trimmed and validated (title/author required, year range, ISBN check-digit). On success `Store.Create` inserts the row and re-reads it to return the server-assigned id, and the handler responds `201` with a `Location` header. Deviations from the minimal pattern: ISBN-10/13 checksum validation, case-insensitive author filtering via `COLLATE NOCASE`, single-connection pool to avoid SQLite write locks, and graceful shutdown on SIGINT/SIGTERM in `main.go`.
