# Flow

```mermaid
sequenceDiagram
    Client->>server.ex: POST /books {json}
    server.ex->>server.ex: read_request / parse headers+body
    server.ex->>router.ex: dispatch("POST","/books",body,%{})
    router.ex->>json.ex: decode(body)
    json.ex-->>router.ex: {:ok, map}
    router.ex->>router.ex: validate(title/author present)
    router.ex->>store.ex: create(book)
    store.ex->>sqlite3: INSERT ...; SELECT last_insert_rowid()
    sqlite3-->>store.ex: row json
    store.ex-->>router.ex: book map
    router.ex-->>server.ex: {201, json}
    server.ex-->>Client: HTTP/1.1 201 Created {json}
```

A `POST /books` is read by the raw-TCP server, which hand-parses the HTTP request line, headers, and `Content-Length`-delimited body, then calls `Router.dispatch/4`. The router decodes the JSON body with the in-house `BookApi.JSON`, rejects a non-object or a missing/blank `title`/`author` with `422` (invalid JSON yields `400`), and otherwise asks `BookApi.Store` to persist. The Store GenServer serializes every DB operation and executes it by shelling out to the `sqlite3` CLI with string-interpolated SQL (string values are single-quote-escaped), returning the inserted row which the router serializes back as `201`. Notable deviations from common Elixir practice: no Plug/Cowboy/Phoenix and no Ecto — the HTTP server, router, and JSON codec are all hand-rolled, and persistence is a `System.cmd("sqlite3", ...)` subprocess per query rather than a database driver.
