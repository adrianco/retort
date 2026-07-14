# Flow

```mermaid
sequenceDiagram
    Client->>handler.go: POST /books {title,author,...}
    handler.go->>handler.go: json.Decode + validate title/author
    handler.go->>store.go: s.create(Book)
    store.go->>store.go: INSERT INTO books; LastInsertId
    store.go-->>handler.go: Book{ID}
    handler.go-->>Client: 201 {json}
```

A request to `POST /books` decodes the JSON body into a `Book`, rejects it with `400` if `title` or `author` is empty, then calls `sqliteStore.create`, which runs a parameterized `INSERT` and reads back the auto-increment id. The populated book is returned as `201 Created`. Errors from the DB layer surface as `500`. The same validation gate is applied on `PUT`. Persistence is real SQLite (`modernc.org/sqlite`, cgo-free); tests inject a `:memory:` store through the `store` interface.
