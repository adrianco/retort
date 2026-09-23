# Summary: effort=low language=c model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Plain C (POSIX sockets) HTTP/1.1 CRUD service with SQLite storage; no framework.
- **Structure:** 3 source modules (books.c/.h, server.c) + 1 test file (5 test functions).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); 2 exported functions.
- **Notable:** Transport separated from logic (`books_handle` is socket-independent, tested directly against `:memory:`); hand-written flat-JSON parser and emitter with escaping and `\uXXXX` handling; URL-decoding of the author filter. Compact (~560 LOC) and idiomatic for freestanding C.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
