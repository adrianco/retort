# Flow

```mermaid
sequenceDiagram
    Client->>handlers.rs: POST /books {title, author, year, isbn}
    handlers.rs->>models.rs: BookInput::validate()
    models.rs-->>handlers.rs: Ok(())
    handlers.rs->>lib.rs: conn.lock()
    lib.rs-->>handlers.rs: Connection
    handlers.rs->>db.rs: insert_book(&conn, &input)
    db.rs-->>handlers.rs: Book { id, .. }
    handlers.rs-->>Client: 201 Created {json Book}
```

A `POST /books` request deserializes into `BookInput` (all fields `#[serde(default)]`, so missing fields are tolerated), then `validate()` rejects empty `title`/`author` with a `400`. On success the handler takes the single `Arc<Mutex<Connection>>` lock, calls `db::insert_book` which executes an `INSERT` and reads `last_insert_rowid()`, and returns the created `Book` as `201`. All DB access is serialized through one mutex-guarded connection, so there is no connection pool and requests contend on a single lock. Errors from SQLite surface as `500` with the error string in the body.
