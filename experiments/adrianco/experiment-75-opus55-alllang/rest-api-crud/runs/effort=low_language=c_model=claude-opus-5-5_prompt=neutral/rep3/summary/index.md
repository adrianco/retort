# Summary: effort=low language=c model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** C11 REST API — hand-written blocking HTTP/1.1 server over BSD sockets, SQLite storage, no external HTTP/JSON libraries.
- **Structure:** 3 source modules (`books.h`/`books.c`/`main.c`) + 1 test file; ~437 source LOC, 90 test LOC.
- **Interfaces:** 7 HTTP routes (health + full CRUD + author filter); 2 exported functions (`books_init_db`, `books_handle`).
- **Notable:** clean transport/logic split makes `books_handle` unit-testable against `:memory:`; hand-rolled JSON parser and URL-decoder; tests compiled with ASan+UBSan and pass clean (30 checks, 0 failures).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
