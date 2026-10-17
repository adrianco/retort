# Flow

```mermaid
sequenceDiagram
    Client->>server.py: POST /books {title, author, ...}
    server.py->>server.py: _read_json() (size + JSON guard)
    server.py->>book_store.py: store.create(data)
    book_store.py->>book_store.py: validate_book(data)
    book_store.py->>SQLite: INSERT ... (lock held)
    SQLite-->>book_store.py: lastrowid
    book_store.py-->>server.py: Book dict
    server.py-->>Client: 201 {json} + Location
```

A `POST /books` reads and size-limits the body, parses it as JSON, then hands it
to `BookStore.create`, which validates (title/author required, year 1–9999, bool
year rejected) before inserting into SQLite under a threading lock. The new row is
re-fetched and returned as JSON with `201` and a `Location` header. All store
operations serialise on a single shared connection guarded by one lock, so the
threaded server never races on the one SQLite connection.
