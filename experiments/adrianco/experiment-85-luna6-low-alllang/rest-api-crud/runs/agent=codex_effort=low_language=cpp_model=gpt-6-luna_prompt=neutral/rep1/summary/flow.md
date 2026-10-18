# Flow

```mermaid
sequenceDiagram
    Client->>main.cpp: POST /books {json}
    main.cpp->>main.cpp: read request, split headers/body
    main.cpp->>BookApi: handle("POST","/books",body)
    BookApi->>BookApi: JsonObjectParser.parse(body)
    BookApi->>BookApi: validate title+author required
    BookApi->>sqlite3: INSERT INTO books(...)
    sqlite3-->>BookApi: last_insert_rowid
    BookApi->>sqlite3: SELECT ... WHERE id=?
    sqlite3-->>BookApi: row
    BookApi-->>main.cpp: HttpResponse{201, book_json}
    main.cpp-->>Client: HTTP/1.1 201 Created {json}
```

A request to `POST /books` is read off the socket in `main.cpp`, which parses the request line and extracts the body using `Content-Length`, then calls `BookApi::handle`. The handler parses the JSON body with a hand-written flat-object parser, enforces that `title` and `author` are non-empty strings (400 otherwise), validates optional `year`/`isbn` types, inserts via a prepared statement, re-selects the created row, and returns it as `201`. Routing is a linear chain of `if` checks keyed on method and path prefix. There is no external HTTP or JSON library — both the TCP server and JSON are hand-rolled. The server is single-threaded and handles one connection at a time (`Connection: close`).
