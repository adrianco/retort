# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: _read_json()
    app.py->>app.py: validate_book(payload)
    app.py->>BookStore: create(clean)
    BookStore->>SQLite: INSERT INTO books
    SQLite-->>BookStore: lastrowid
    BookStore-->>app.py: Book row (dict)
    app.py-->>Client: 201 {json}
```

A `POST /books` reads the request body, parses JSON (`_read_json`), and runs `validate_book`, which requires non-empty string `title` and `author` and type-checks optional `year` (int in range) and `isbn` (ISBN-10/13). On failure it returns `400 {"error":"validation failed","details":{...}}`. On success `BookStore.create` inserts under a lock and returns the persisted row as JSON with `201`. Notable: the whole service uses only the Python standard library (`http.server` + `sqlite3`) with no third-party framework; PUT is a full replacement (title+author required), and the single SQLite connection is shared across threads with `check_same_thread=False` behind one lock.
