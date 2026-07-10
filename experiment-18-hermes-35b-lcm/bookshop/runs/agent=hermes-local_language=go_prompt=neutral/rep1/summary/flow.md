# Flow

```mermaid
sequenceDiagram
    Client->>main.go: POST /books {json}
    main.go->>handlers.go: createBook(w, r)
    handlers.go->>handlers.go: json.Decode into CreateBookRequest
    handlers.go->>handlers.go: validate title/author non-empty
    handlers.go->>database.go: Store.CreateBook(title, author, year, isbn)
    database.go->>database.go: INSERT INTO books; LastInsertId()
    database.go-->>handlers.go: *Book
    handlers.go-->>Client: 201 {book json}
```

A `POST /books` request is routed by the `/books` `mux.HandleFunc` in `main.go`, which switches on method and calls `handlers.go:createBook`. The handler JSON-decodes the body into a `CreateBookRequest`, then checks that `title` and `author` are non-empty, accumulating field-level `ValidationError`s and returning `400 {errors: [...]}` if any fail. On success it calls `BookStore.CreateBook`, which runs a parameterized `INSERT` and reads back the generated ID via `LastInsertId()`, returning a fully populated `Book` written to the client as `201`.

Deviations from common patterns: validation is limited to presence of title/author (no length, ISBN format, or year-range checks); `year` and `isbn` are stored as `NOT NULL` but accepted even when zero/empty from the request. Data is stored in an in-memory SQLite DB (`:memory:`), so all state is lost on restart. There is no pagination on `GET /books` (only an optional `author` equality filter), no request-context/timeout plumbing, and route/ID parsing is done manually with `strings.TrimPrefix` + `strconv.Atoi` rather than a router library. `handlers.go` also defines unused `HandleBooks`/`HandleBookByID` dispatchers that are superseded by the inline closures in `main.go`.
