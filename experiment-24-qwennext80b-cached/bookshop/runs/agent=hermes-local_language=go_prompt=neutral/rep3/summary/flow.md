# Flow

```mermaid
sequenceDiagram
    Client->>app.go: POST /api/books {title,author,year,isbn}
    app.go->>app.go: ShouldBindJSON + required-field checks
    app.go->>SQLite: INSERT INTO books (...)
    SQLite-->>app.go: LastInsertId
    app.go-->>Client: 201 {id,title,author,year,isbn}
```

A `POST /api/books` request is bound into `BookInput` (all four fields flagged
`required` via gin binding), then re-checked for empty title/author before an
`INSERT` into the SQLite `books` table; the new id is returned with 201. Reads
(`GetBooks`, `GetBook`) query the same table directly; `GetBooks` branches on the
`author` query param. Notable: routes are served under `/api` while the spec and
tests use root paths; year/isbn are required beyond the spec; the explicit empty
checks are unreachable because binding already rejects empties.
