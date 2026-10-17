# Flow

```mermaid
sequenceDiagram
    Client->>http_app.py: POST /books {title, author, ...}
    http_app.py->>http_app.py: _dispatch("POST") -> _create_book
    http_app.py->>validation.py: validate_book(payload)
    validation.py-->>http_app.py: cleaned dict (or 400 ValidationError)
    http_app.py->>store.py: BookStore.create(book)
    store.py->>store.py: INSERT INTO books (locked SQLite conn)
    store.py-->>http_app.py: {id, title, author, year, isbn}
    http_app.py-->>Client: 201 {json} + Location: /books/{id}
```

A request is routed by `_dispatch`, which matches the path against the `ROUTES` regex table and selects a handler by HTTP method (JSON 405 with `Allow` for a known path + wrong method, JSON 404 otherwise). `_create_book` reads and JSON-parses the body (enforcing `Content-Length` and a 1 MiB cap), validates it via `validate_book` (title/author required, optional year range and ISBN-10/13 checksum), and persists via `BookStore`, which guards a single shared SQLite connection with a `threading.Lock`. All responses are JSON with explicit status codes. Threaded server (`ThreadingHTTPServer`) with daemon threads; no auth, no pagination (full list, optional exact case-insensitive author filter).
