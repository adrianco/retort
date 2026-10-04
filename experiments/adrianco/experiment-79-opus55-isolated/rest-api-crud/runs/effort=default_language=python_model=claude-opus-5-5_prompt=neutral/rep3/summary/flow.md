# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {json}
    app.py->>app.py: read_json(environ)
    app.py->>app.py: validate_book(data)
    app.py->>BookStore: create(book)
    BookStore->>SQLite: INSERT ... ; SELECT by id
    SQLite-->>BookStore: row
    BookStore-->>app.py: book dict
    app.py-->>Client: 201 {json Book}
```

A `POST /books` request is dispatched by the single `route()` function inside
`create_app`. It reads and size-limits the body (`read_json`, 1 MB cap),
validates it (`validate_book` — `title`/`author` required and trimmed, `year`
an optional bounded int, `isbn` an optional string), then calls
`BookStore.create`, which opens a per-operation SQLite connection, inserts the
row, and reads it back. The WSGI wrapper serializes the returned dict to JSON,
sets `Content-Type`/`Content-Length`, and emits `201 Created`. Errors are raised
as `ApiError` and rendered to the appropriate status with an `{"error": ...}`
body (validation failures also carry a per-field `details` map); unexpected
exceptions become a `500`.
