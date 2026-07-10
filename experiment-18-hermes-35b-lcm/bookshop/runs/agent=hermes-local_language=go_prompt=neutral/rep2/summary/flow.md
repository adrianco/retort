# Flow

```mermaid
sequenceDiagram
    Client->>handlers.go: POST /books {title,author,year,isbn}
    handlers.go->>handlers.go: HandleBooks dispatch (path=="/books", POST)
    handlers.go->>handlers.go: json.Decode -> validateCreate
    alt title/author blank
        handlers.go-->>Client: 400 {error, validation[]}
    else valid
        handlers.go->>database.go: CreateBook(title,author,year,isbn)
        database.go->>database.go: INSERT INTO books ...
        database.go-->>handlers.go: *Book (with id)
        handlers.go-->>Client: 201 {book json}
    end
```

A `POST /books` enters `HandleBooks`, which matches the exact `/books` path and
POST method and delegates to `HandleCreateBook`. The body is JSON-decoded into
`CreateBookRequest`; `validateCreate` rejects blank `title`/`author` with a 400
carrying per-field validation errors. On success `database.go:CreateBook` inserts
the row and returns the persisted `Book`, which is emitted as 201 JSON.

Notable deviations from common patterns:
- Routing is hand-rolled (no router library); `{id}` is parsed via string prefix
  trimming + `strconv.Atoi`.
- Create-time validation is enforced, but `UpdateBook` (PUT) applies no validation —
  a partial update can blank a required field.
- `?author=` uses a SQL `LIKE '%...%'` substring match rather than exact equality.
- Health timestamp is a Unix-epoch string rather than RFC3339.
