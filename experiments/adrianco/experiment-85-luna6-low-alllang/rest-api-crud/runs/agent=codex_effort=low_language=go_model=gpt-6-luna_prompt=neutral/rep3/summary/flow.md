# Flow

```mermaid
sequenceDiagram
    Client->>main.go: POST /books {title,author,year,isbn}
    main.go->>main.go: decodeBook (DisallowUnknownFields, reject trailing JSON)
    main.go->>main.go: validate (title & author required)
    main.go->>SQLite: INSERT INTO books(...)
    SQLite-->>main.go: LastInsertId
    main.go-->>Client: 201 {Book}
```

A request to `POST /books` is routed by `API.ServeHTTP` (a hand-rolled path
switch, no framework). The body is decoded with `DisallowUnknownFields` and a
1 MiB cap, rejecting unknown or trailing JSON with 400. `validate` enforces
non-empty title and author (trimmed). The row is inserted via a parameterized
query and the new id is read back from `LastInsertId`. Errors return JSON error
objects with matching status codes. Routing distinguishes `/books` (collection)
from `/books/{id}` (item) by path prefix and rejects nested/empty ids. DB access
is synchronous with `SetMaxOpenConns(1)`.
