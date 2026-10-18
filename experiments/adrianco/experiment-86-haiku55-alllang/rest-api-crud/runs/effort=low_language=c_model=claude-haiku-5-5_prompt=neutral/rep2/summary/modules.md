# Modules

A book-collection REST API in C11, serving JSON over HTTP/1.1 on raw POSIX
sockets, persisting to SQLite. The only external dependency is `libsqlite3`.

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.c | Process entry: read `PORT`/`DB_PATH`, open store, listen, serve | `main` |
| src/http.c | HTTP/1.1 request parsing, connection loop, response writing, query-param percent-decode | `http_parse_head`, `query_param`, `http_listen`, `http_serve` |
| src/api.c | Route dispatch, request validation, JSON serialization of books | `api_handle`, `api_response_free` |
| src/db.c | SQLite store: schema, prepared-statement CRUD, row mapping | `store_open`, `store_close`, `store_create`, `store_find`, `store_list`, `store_update`, `store_delete`, `book_clear`, `books_free` |
| src/json.c | Recursive-descent JSON object parser (strings, numbers, escapes, surrogates) | `json_parse_object`, `json_get`, `json_object_free`, `json_write_string` |
| src/strbuf.c | Growable string buffer for building responses | `sb_init`, `sb_append`, `sb_puts`, `sb_putc`, `sb_steal`, `sb_free` |
| src/util.c | Allocation wrappers and hex-digit helper | `xmalloc`, `xrealloc`, `xstrndup`, `xstrdup`, `hex_digit_value` |
| tests/test_all.c | Hand-rolled assertion harness: 9 test functions, 89 `CHECK` assertions | `main` |

Headers (`src/*.h`) declare the interfaces for each module; no build artifacts
are present in the archive (the `build/` tree is produced by `make`).
