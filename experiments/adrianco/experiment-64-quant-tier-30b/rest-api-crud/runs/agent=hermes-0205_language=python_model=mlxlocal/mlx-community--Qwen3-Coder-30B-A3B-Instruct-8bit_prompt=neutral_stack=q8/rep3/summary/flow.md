# Flow

```mermaid
sequenceDiagram
    Client->>main.py: POST /books {title, author, year, isbn}
    main.py->>BookCreate: pydantic validation
    BookCreate-->>main.py: BookCreate | 422
    main.py->>books.db: sqlite3.connect(DB_NAME)
    main.py->>books.db: INSERT INTO books (...) VALUES (?,?,?,?)
    books.db-->>main.py: cursor.lastrowid
    main.py->>books.db: commit(); close()
    main.py-->>Client: 200 {id, title, author, year, isbn}
```

A `POST /books` request is first validated by the `BookCreate` Pydantic model, which makes `title` and `author` mandatory — a missing field yields FastAPI's default 422, not the 400 the task spec illustrates. The handler then opens a fresh `sqlite3` connection per request (no pooling, no context manager, no `try/finally`, so a failing `INSERT` leaks the connection), inserts the row, reads back `lastrowid`, commits, closes, and returns the book echoed from the request payload rather than re-read from the database. Creation returns FastAPI's default 200 rather than 201. The schema is created lazily by `init_db()` bound to `@app.on_event("startup")`, a FastAPI API deprecated in favour of `lifespan`; importing `main` without going through the ASGI startup path (as `basic_test.py` does) therefore does not create the table.

Deviations worth noting for cross-run comparison: no pagination on `GET /books`; `?author=` is a `LIKE '%…%'` substring match rather than an exact match; error handling covers only 404 (missing id) and 400 (empty `PUT` body) — SQLite exceptions are unhandled; database access is synchronous inside `def` (not `async def`) handlers, which FastAPI runs on a threadpool, so this is safe but untuned.
