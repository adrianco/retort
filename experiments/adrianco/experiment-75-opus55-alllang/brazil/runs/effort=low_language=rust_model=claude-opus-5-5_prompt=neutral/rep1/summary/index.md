# Summary: effort=low_language=rust_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Rust MCP (JSON-RPC 2.0 / stdio) server over Brazilian soccer CSV datasets; `csv` + `serde_json`, no async, no framework.
- **Structure:** 4 source modules (main/lib/data/query/mcp) + 1 test file (31 BDD scenarios).
- **Interfaces:** MCP handshake + 12 tools (match/team/player/competition/stats queries), 1 CLI binary.
- **Notable:** Unusually complete for a low-effort run — cross-file de-duplication, accent-folding team-name canonicalization with hand-tuned aliases, multi-format date parsing, computed standings with champion/relegation, and a cross-file player↔match join. Only 2 dependencies.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
