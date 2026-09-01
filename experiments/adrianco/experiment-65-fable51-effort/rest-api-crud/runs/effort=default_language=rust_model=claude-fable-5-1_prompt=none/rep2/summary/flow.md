# Flow

```mermaid
sequenceDiagram
    Client->>handlers.rs: POST /books {title,author,...}
    handlers.rs->>models.rs: BookInput.validate()
    models.rs-->>handlers.rs: ValidBook | Err(400)
    handlers.rs->>AppState: db.lock()
    handlers.rs->>db.rs: insert(conn, ValidBook)
    db.rs-->>handlers.rs: Book
    handlers.rs-->>Client: 201 {json Book}
```

A `POST /books` request is deserialized into `BookInput`; a `JsonRejection` on
malformed bodies is mapped to a 400 with a JSON error. `BookInput::validate()`
trims and requires non-blank `title` and `author` (and bounds `year`), returning
a `ValidBook` or a list of validation errors (400). The handler locks the shared
`Arc<Mutex<Connection>>`, calls `db::insert`, and returns 201 with the created
record. Unique-constraint violations on `isbn` surface as 409 Conflict via the
`From<rusqlite::Error>` mapping in `error.rs`. DB access is synchronous behind a
mutex inside async handlers.
