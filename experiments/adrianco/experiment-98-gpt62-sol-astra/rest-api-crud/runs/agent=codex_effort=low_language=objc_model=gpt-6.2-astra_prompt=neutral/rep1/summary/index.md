# Summary: agent=codex effort=low language=objc model=gpt-6.2-astra prompt=neutral · rep 1

- **Shape:** Hand-rolled Objective-C (Foundation) HTTP/1.1 CRUD service over the system SQLite library — no web framework.
- **Structure:** 1 source module (`Books.m`, 161 lines), 1 test file (`test_books.py`, 4 tests), Makefile + README.
- **Interfaces:** 7 HTTP routes (health + full books CRUD + author filter); one `books` SQLite table.
- **Notable:** Extremely compact single-file implementation; parameterized SQL with `RETURNING` everywhere; a `--stdio` single-request mode that the Python tests drive instead of a live socket. Explicit hardening (Transfer-Encoding rejected, 1 MiB body cap, socket timeouts).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
