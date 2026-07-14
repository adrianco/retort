# Summary: language=elixir_model=opus-4.8-fast_prompt=neutral · rep 1

- **Shape:** Elixir/OTP MCP server (hand-rolled JSON-RPC stdio transport) over an in-memory store of six Brazilian-soccer Kaggle CSVs; query modules + a `BrSoccer` facade + a text `Format` layer.
- **Structure:** 19 lib modules, 6 test files (+ shared fixtures); single dependency (`jason`).
- **Interfaces:** 15 MCP tools, 4 JSON-RPC methods (`initialize`/`tools/list`/`tools/call`/`ping`), an escript CLI (`--ask` one-shot mode), and a ~15-function `BrSoccer` library API.
- **Notable:** Zero third-party parsing/protocol libs — both the RFC 4180 CSV parser and the MCP transport are written from scratch; data is loaded once and cached in `:persistent_term` for lock-free in-memory queries; overlapping fixtures are de-duplicated by source priority; the protocol layer (`handle_message/1`) is pure and I/O-free for testability.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
