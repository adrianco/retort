# Flow

```mermaid
sequenceDiagram
    Client->>main.go: POST /books {title,author,year,isbn}
    main.go->>handlers.go: API.CreateBook(w, r)
    handlers.go->>handlers.go: decode JSON + validate title/author
    handlers.go->>models.go: BookStore.Create(req)
    models.go->>SQLite: INSERT INTO books ...
    SQLite-->>models.go: LastInsertId
    models.go-->>handlers.go: *Book
    handlers.go-->>Client: 201 {json Book}
```

A `POST /books` request is routed by the Go 1.22 method-aware `ServeMux` to `API.CreateBook`, which decodes the JSON body, rejects empty `title` or `author` with `400`, then calls `BookStore.Create` to `INSERT` a row into the SQLite `books` table. A `UNIQUE` violation on `isbn` is surfaced as `409 Conflict`; success returns `201` with the created book (including generated id and created_at). Persistence is a real embedded SQLite file (`modernc.org/sqlite`, pure-Go), not in-memory state.
