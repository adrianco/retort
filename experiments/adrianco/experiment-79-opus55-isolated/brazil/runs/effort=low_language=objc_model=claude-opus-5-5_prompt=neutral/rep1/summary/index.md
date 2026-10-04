# Summary: effort=low_language=objc_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Objective-C (Foundation-only, ARC) MCP server over stdio for Brazilian soccer data, with a query engine over six merged Kaggle CSVs.
- **Structure:** 7 source modules (13 `.h`/`.m` files) + 1 test file; built with a hand-written Makefile.
- **Interfaces:** JSON-RPC 2.0 MCP protocol (initialize/tools/list/tools/call/ping/batch) exposing 17 tools; CLI also supports `--list-tools` and `--call`.
- **Notable:** Data-layer sophistication well beyond spec — cross-file fixture de-duplication, accent/suffix-insensitive team-name resolution, derby detection, title-decided/relegation heuristics, incomplete-season honesty. In-band tool errors. 41 BDD scenarios / 145 checks including an end-to-end stdio subprocess test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
