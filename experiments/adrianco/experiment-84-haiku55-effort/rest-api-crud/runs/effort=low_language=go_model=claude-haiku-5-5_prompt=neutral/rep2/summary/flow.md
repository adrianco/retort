# Flow

```mermaid
sequenceDiagram
    Client->>api.go: POST /books {json}
    api.go->>book.go: decode + Normalize + Validate
    book.go-->>api.go: BookInput (or 400/422)
    api.go->>store.go: Create(in)
    store.go->>SQLite: INSERT ... RETURNING id
    SQLite-->>store.go: id
    store.go-->>api.go: Book
    api.go-->>Client: 201 {json} + Location
```

A `POST /books` request is read with a 1 MiB body cap, JSON-decoded into
`BookInput`, trimmed by `Normalize`, then `Validate` enforces required
title/author, non-negative year, and ISBN-10/13 shape — returning 400 on
malformed JSON and 422 on validation failure. On success the handler calls
`Store.Create`, which inserts into the SQLite `books` table and returns the
row with its assigned id, serialized as 201 JSON with a `Location` header.
The author filter is pushed into SQL (`WHERE author = ? COLLATE NOCASE`).
