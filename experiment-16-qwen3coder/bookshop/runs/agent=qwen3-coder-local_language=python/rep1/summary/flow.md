# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>app.py: validate title & author present
    alt missing title/author
        app.py-->>Client: 400 {error}
    else valid
        app.py->>Book: Book(...) + db.session.add/commit
        Book-->>app.py: persisted row (id, timestamps)
        app.py-->>Client: 201 {book json}
    end
```

A request to `POST /books` parses JSON, rejects the payload with 400 if `title`
or `author` is missing (`app.py:53`), otherwise constructs a `Book`, commits it
to the SQLite-backed session, and returns the serialized row with 201. Write
failures are caught and rolled back to a 500. The same file-based `books.db` is
shared by the app and by `tests.py`'s `setUp`/`tearDown`, which call
`db.create_all()`/`db.drop_all()` against the real database rather than an
isolated in-memory one.
