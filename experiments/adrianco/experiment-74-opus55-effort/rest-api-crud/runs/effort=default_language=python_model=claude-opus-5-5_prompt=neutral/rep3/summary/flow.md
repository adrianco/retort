# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {json}
    app.py->>app.py: _read_json() (Content-Length guarded)
    app.py->>app.py: validate_book(data)
    app.py->>BookStore: create(book)
    BookStore->>sqlite3: INSERT INTO books ...
    sqlite3-->>BookStore: lastrowid
    BookStore-->>app.py: {id, title, author, year, isbn}
    app.py-->>Client: 201 {json} + Location header
```

A `POST /books` request is read with a `Content-Length` bound (max 1 MB) and JSON-decoded; `validate_book` enforces required non-empty `title`/`author`, an integer `year` in range, an ISBN-10/13-shaped `isbn`, and rejects unknown fields (422 with per-field `details` on failure). On success `BookStore.create` inserts under a `threading.Lock` and returns the persisted row, which is sent as 201 with a `Location: /books/{id}` header. The server is threaded (`ThreadingHTTPServer`) with a single shared SQLite connection (`check_same_thread=False`) serialized by the lock; persistence is real (file-backed SQLite by default).
