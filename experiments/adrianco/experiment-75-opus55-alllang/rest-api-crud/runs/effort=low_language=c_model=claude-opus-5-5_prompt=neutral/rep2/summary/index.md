# Summary: effort=low language=c model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Plain-C HTTP/1.1 REST API on POSIX sockets, no framework, SQLite persistence, hand-written JSON parser/emitter.
- **Structure:** 3 source modules (books.h/books.c/server.c) + 2 test files, 1 Makefile.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with ?author= filter); 2-function C library API (`books_open`, `books_handle`); 1 SQLite table.
- **Notable:** Clean separation of routing/DB logic (`books.c`) from transport (`server.c`), which makes the handler directly unit-testable against an in-memory DB. Careful edge handling: JSON escaping/`\uXXXX`, URL-decoding of query params, type validation, request-size cap, prepared statements (no SQL injection). Single-threaded sequential server; no pagination.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
