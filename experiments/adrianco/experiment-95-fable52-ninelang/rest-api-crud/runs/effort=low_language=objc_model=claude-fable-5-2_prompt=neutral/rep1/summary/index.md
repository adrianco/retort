# Summary: effort=low_language=objc_model=claude-fable-5-2_prompt=neutral · rep 1

- **Shape:** Objective-C REST API using only system frameworks — Foundation, raw BSD sockets for HTTP/1.1, and `libsqlite3` for storage. No third-party dependencies.
- **Structure:** 4 source modules (BookStore, BooksAPI, HTTPServer, main) + 1 test file (8 test functions), built with a hand-written Makefile.
- **Interfaces:** 7 HTTP routes (health + 5 book CRUD + method-not-allowed fallbacks), transport-independent router (`BooksAPI`) decoupled from the socket server.
- **Notable:** Clean layering separates the router from the transport, so most tests exercise `BooksAPI` directly (fast) with one real-socket end-to-end test. Thread-safe SQLite store (NSLock-serialised), parameterised SQL (SQLi-safe), and a deliberately richer validation scheme (422 for semantic validation, 400 for malformed JSON).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
