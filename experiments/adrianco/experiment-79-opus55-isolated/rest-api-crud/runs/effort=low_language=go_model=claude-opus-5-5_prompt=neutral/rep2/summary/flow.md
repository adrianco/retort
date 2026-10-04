# Flow

```mermaid
sequenceDiagram
    Client->>handlers.go: POST /books {json}
    handlers.go->>handlers.go: decodeBook (MaxBytesReader, validate)
    handlers.go->>store.go: Create(&Book)
    store.go->>SQLite: INSERT INTO books
    SQLite-->>store.go: LastInsertId
    store.go-->>handlers.go: nil err, b.ID set
    handlers.go-->>Client: 201 + Location + {book json}
```

A `POST /books` request is decoded by `decodeBook`, which caps the body at 1 MB,
rejects malformed/trailing JSON with 400, and enforces that `title` and `author`
are non-blank (and `year >= 0`) via `bookInput.validate()`. On success it calls
`Store.Create`, which inserts a row and back-fills the generated ID, then returns
201 with a `Location` header and the JSON book. Errors are uniformly JSON
(`errorBody`), with per-field detail for validation failures; not-found maps to
404, other store errors to a logged 500. Persistence is real SQLite, verified by
`TestPersistsAcrossReopen`.
