# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: POST /books {title, author, year, isbn}
    main.rs->>main.rs: validate(input) (title/author non-empty)
    main.rs->>SQLite: INSERT INTO books ...
    SQLite-->>main.rs: last_insert_rowid()
    main.rs->>SQLite: SELECT ... WHERE id = ?
    SQLite-->>main.rs: Book row
    main.rs-->>Client: 201 {json Book}
```

A `POST /books` request is deserialized into `BookInput`, validated (empty/whitespace
`title` or `author` → 400), inserted into the SQLite `books` table, then re-selected by
`last_insert_rowid()` and returned as a JSON `Book` with 201 Created. All handlers share
a `SqlitePool` via `State<AppState>`; errors flow through the `ApiError` enum, which
implements `IntoResponse` to emit `{"error": msg}` with the matching status code. No
pagination; the `?author=` filter is an exact-match SQL equality.
