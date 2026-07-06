# Flow

```mermaid
sequenceDiagram
    Client->>handlers.go: POST /books {json}
    handlers.go->>models.go: Book.Validate()
    models.go-->>handlers.go: ok / error
    handlers.go->>store.go: Store.Create(book)
    store.go->>SQLite: INSERT ... RETURNING id
    SQLite-->>store.go: LastInsertId
    store.go-->>handlers.go: Book{ID}
    handlers.go-->>Client: 201 {json}
```

A `POST /books` request is JSON-decoded into a `Book`, validated for required
`title`/`author` (400 on failure), then inserted via `Store.Create`, which
executes a parameterized `INSERT` and stamps the assigned auto-increment ID
onto the returned book, serialized as `201 Created`. Errors are consistently
surfaced through `writeError` as JSON `{error}` bodies. `ErrNotFound` from the
store maps to 404 on the id-scoped routes. All queries are parameterized (no
SQL injection); no pagination on the list route.
