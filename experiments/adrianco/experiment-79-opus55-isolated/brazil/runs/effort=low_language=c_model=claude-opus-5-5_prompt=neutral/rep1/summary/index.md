# Summary: effort=low_language=c_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** C11 MCP server (JSON-RPC over stdio) with hand-written JSON parser and in-memory CSV knowledge base for Brazilian soccer.
- **Structure:** 9 source files (~3,581 lines src), 2 test files (~714 lines); no third-party dependencies (libc + libm only).
- **Interfaces:** 4 MCP JSON-RPC methods, 15 registered tools spanning match / team / player / competition / statistical queries; also a `--call` CLI mode.
- **Notable:** Cross-dataset de-duplication and team-name normalization (accent folding, state suffixes, aliases); standings/head-to-head computed from raw matches, not hardcoded; from-scratch JSON parser rather than a library.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
