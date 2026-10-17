# Flow

```mermaid
sequenceDiagram
    Client->>app.py: POST /books {title, author, year, isbn}
    app.py->>validation.py: parse_book(body)
    validation.py-->>app.py: cleaned book (or ValidationError -> 400)
    app.py->>database.py: insert_book(conn, book)
    database.py-->>app.py: book with id
    app.py-->>Client: 201 {json} + Location header
```

A request to `POST /books` reads the JSON body (accepted even without a `Content-Type` header via `force=True`), validates it through `validation.parse_book()` which collects every field error at once and raises `ValidationError` (mapped to a 400 JSON response) if any field is bad. On success the cleaned record is inserted via a per-request SQLite connection managed by Flask's `g`/`teardown_appcontext`, and the new book is returned as 201 JSON with a `Location` header. Input validation, structured error handling (400/404/405/500), and SQLite persistence are all present; the author filter is a case-insensitive, accent-aware substring match.
