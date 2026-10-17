# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {json}
    server.go->>server.go: decodeBookInput (MaxBytes, DisallowUnknownFields)
    server.go->>book.go: normalize() + Validate()
    book.go-->>server.go: ok (or 400 ValidationErrors)
    server.go->>store.go: Create(BookInput)
    store.go->>store.go: INSERT INTO books
    store.go-->>server.go: Book{ID,...} (or ErrISBNConflict)
    server.go-->>Client: 201 {json} + Location header
```

A `POST /books` request is size-capped and JSON-decoded with unknown-field and
trailing-content rejection, normalized (trim, canonicalize ISBN) and validated
(title/author required, optional year range and ISBN format). On success the
handler inserts via `store.go:Create`, which maps a unique-ISBN violation to
`ErrISBNConflict` (409). The created book is returned as `201` JSON with a
`Location` header. Error mapping is centralized in `writeStoreError`
(404/409/500) and `writeValidationError` (400).
