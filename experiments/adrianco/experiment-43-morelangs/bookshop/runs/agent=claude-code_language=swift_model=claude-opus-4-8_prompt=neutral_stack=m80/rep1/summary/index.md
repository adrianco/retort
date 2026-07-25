# Summary: swift · claude-code · m80 · rep 1

- **Shape:** Swift REST API with a hand-rolled HTTP/1.1 server on Apple's `Network` framework and a SQLite-backed store — zero external dependencies.
- **Structure:** 6 source modules (BookAPI library + BookServer executable), 3 test files (20 test functions).
- **Interfaces:** 7 HTTP routes (health + full CRUD with `?author=` filter), library API for `BookStore`/`Router`/`HTTPServer`, one `books` SQLite table.
- **Notable:** Clean separation of parsing/routing/storage makes the `Router` fully testable without networking; thread-safety via a serialized dispatch queue; no third-party packages so it builds offline.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
