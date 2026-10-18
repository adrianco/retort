# Summary: brazil · effort=low language=cpp model=claude-haiku-5-5 prompt=neutral · rep 2

- **Shape:** C++17 MCP (JSON-RPC over stdio) server for Brazilian soccer data, with a hand-written JSON/CSV layer and an in-memory store over 6 Kaggle CSVs. Built with CMake (`soccer_core` lib + exe + tests).
- **Structure:** 9 source modules (paired .h/.cpp), ~1900 lines total; 4 test files (35 `TEST` cases across core/data/server) plus a tiny custom test framework.
- **Interfaces:** 4 MCP methods (initialize/ping/tools/list/tools/call) exposing 9 tools; 1 CLI binary with `--data-dir`; no HTTP.
- **Notable:** No third-party dependencies — JSON parser/serializer and RFC-4180 CSV reader are written from scratch. Careful team-name normalization (state-suffix stripping, accent folding) and CSV dedup/overlap handling. Clean layering (main → mcp_server → tools → queries → data_store/team/text/csv/json). scores.json: code_quality 1.0, test_coverage 1.0, defect_rate 1.0, idiomatic 0.82.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
