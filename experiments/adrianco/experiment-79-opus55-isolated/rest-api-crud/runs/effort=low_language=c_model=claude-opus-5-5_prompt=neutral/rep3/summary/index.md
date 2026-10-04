# Summary: effort=low_language=c_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Plain C11 REST API on POSIX sockets with SQLite storage; no dependencies beyond libc and libsqlite3.
- **Structure:** 3 source files (api.c, api.h, main.c), 2 test files (test_api.c, smoke.sh).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); 2 exported functions.
- **Notable:** Hand-rolled JSON parser/serializer and growable string buffer; parameterized SQL (injection-safe); UTF-8 `\u` escape handling incl. surrogate pairs. Clean separation of routing/DB (api.c) from the HTTP server (main.c).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
