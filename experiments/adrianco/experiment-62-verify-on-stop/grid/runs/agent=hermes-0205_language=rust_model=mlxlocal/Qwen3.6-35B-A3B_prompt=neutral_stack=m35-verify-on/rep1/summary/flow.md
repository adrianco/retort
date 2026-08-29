# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: POST /books {title,author,...}
    main.rs->>main.rs: db.lock() (Mutex<Connection>)
    main.rs->>database.rs: create_book(&conn, req)
    database.rs->>database.rs: validate title/author
    database.rs->>SQLite: INSERT INTO books (...)
    Note over SQLite: live server conn has NO books table
    SQLite-->>database.rs: Err "no such table: books"
    database.rs-->>main.rs: Err(msg)
    main.rs-->>Client: 400 {error}
```

A request to `POST /books` locks the shared `Mutex<rusqlite::Connection>`, validates that `title` and `author` are present and non-empty, then inserts a UUID-keyed row. Under `cargo test` the flow succeeds because each test builds its own connection and runs `TABLE_DEF` on it. **At runtime the live server is broken:** `main()` creates the served connection with `Connection::open_in_memory()` but never applies `TABLE_DEF` to it — the schema is instead created on a *separate*, immediately-discarded connection opened at path `"in-memory"` (`create_connection("in-memory").ok()`). So the served connection has no `books` table, and every DB-touching route would fail at runtime. This is the exact "schema created on a discarded connection" regression FEEDBACK.md flagged, and it was not fixed.
