# Control Flow

## Happy Path: Create and Retrieve a Book

```mermaid
sequenceDiagram
    Client->>main.py: POST /books {title, author, year?, isbn?}
    main.py->>BookCreate: validate(title, author)
    BookCreate-->>main.py: validated payload
    main.py->>SQLite: INSERT INTO books (...)
    SQLite-->>main.py: new row with id
    main.py-->>Client: 201 {id, title, author, year, isbn}
    
    Client->>main.py: GET /books/{id}
    main.py->>SQLite: SELECT * FROM books WHERE id = ?
    SQLite-->>main.py: Book row or NULL
    alt Found
        main.py-->>Client: 200 {Book}
    else Not Found
        main.py-->>Client: 404 {detail: "Book not found"}
    end
```

**Narration:** A client POST-ing a book triggers Pydantic validation of required fields (title, author must be non-empty). On success, the book is inserted into the SQLite `books` table and the new row (with auto-generated id) is returned as JSON with 201 Created. A subsequent GET request to `/books/{id}` opens a new database connection, queries by ID, and returns the row as JSON (200) or raises a 404 HTTPException if not found. All database connections are properly closed via `contextlib.closing()`.
