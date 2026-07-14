# Flow

```mermaid
sequenceDiagram
    Client->>main.py: POST /books {title, author, year, isbn}
    main.py->>schemas.py: validate BookCreate (title/author min_length=1)
    schemas.py-->>main.py: BookCreate | 422
    main.py->>crud.py: create_book(book)
    crud.py->>database.py: get_connection()
    database.py-->>crud.py: sqlite3.Connection
    crud.py-->>main.py: book_id (lastrowid)
    main.py-->>Client: 201 {id, title, author, year, isbn}
```

A `POST /books` request is validated by the `BookCreate` Pydantic model (missing/empty `title` or `author` yields a 422 before any handler code runs). The handler calls `crud.create_book`, which opens a fresh SQLite connection per call, inserts the row, commits, and returns `lastrowid`. The handler echoes the created book with its new id at status 201. Each CRUD function opens and closes its own connection (no pooling); the DB path is env-var overridable (`BOOKS_DB_PATH`), which the test fixture uses for per-test isolation. Layering is clean: routing (main) → validation (schemas) → data access (crud) → connection (database).
