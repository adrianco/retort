# Summary: effort=low_language=cpp_model=claude-haiku-5-5_prompt=neutral · rep 1

- **Shape:** C++17 stdio MCP server (JSON-RPC 2.0) with a hand-rolled JSON + CSV layer over in-memory Kaggle datasets.
- **Structure:** 13 source modules (7 src pairs + tests), 4 test files, ~1,864 src LOC / ~2,421 total.
- **Interfaces:** 4 JSON-RPC methods + 6 MCP tools; ~7 exported query functions; 0 external dependencies (std library only).
- **Notable:** No third-party deps at all — JSON, CSV and the test harness are all hand-written. Fixtures are deduplicated across overlapping competition sources; standings/stats are computed, not stored.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
