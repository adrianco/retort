# Summary: agent=codex effort=low language=objc model=gpt-6.2-sol prompt=neutral · rep 1

- **Shape:** Objective-C (Foundation, ARC) stdio JSON-RPC MCP server over the Brazilian soccer CSVs, built with clang.
- **Structure:** 3 source modules (`main.m`, `Soccer.m`, `Soccer.h`) + 1 Python test file (`tests.py`), plus a `Makefile`.
- **Interfaces:** 1 stdio MCP transport (JSON-RPC: `initialize`, `ping`, `tools/list`, `tools/call`) exposing 6 MCP tools; no HTTP/CLI subcommands.
- **Notable:** A single 826-line `Soccer.m` does all CSV parsing, team-name normalization (accent folding, state-suffix handling, alias/regional disambiguation), cross-file fixture de-duplication/merging, standings computation, and FIFA roster joins. Hand-written RFC-4180-style CSV reader (quotes, embedded newlines, BOM). Very dense; low per-line idiomatic/maintainability scores but high correctness.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
