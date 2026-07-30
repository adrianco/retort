# Flow

```mermaid
sequenceDiagram
    Client->>server.go: POST /books {title,author,...}
    server.go->>server.go: decodeInput (MaxBytes + DisallowUnknownFields)
    server.go->>book.go: BookInput.toBook() (validate)
    book.go-->>server.go: Book | *ValidationError(400)
    server.go->>store.go: Store.Create(book)
    store.go->>SQLite: INSERT ... RETURNING id
    SQLite-->>store.go: id
    store.go-->>server.go: Book{ID:...}
    server.go-->>Client: 201 {json} + Location header
```

A `POST /books` request is decoded with a 1 MiB body cap and `DisallowUnknownFields`,
then validated by `BookInput.toBook()` — `title` and `author` are required (trimmed),
`year` is range-checked (0–2200). Validation failures return `400` with a per-field
`fields` map and persist nothing. On success the row is inserted into SQLite, the
generated ID is attached, and the book is returned as `201` JSON with a `Location`
header. Errors are centralised in `writeError`, which maps `*ValidationError`→400,
`ErrNotFound`→404, and anything else→500. The server uses signal-based graceful
shutdown and a single SQLite connection (write serialisation / stable `:memory:`).
