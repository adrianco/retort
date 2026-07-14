# Summary: language=python · model=opus-4.8-fast · prompt=neutral · rep 3

- **Shape:** Python MCP server (FastMCP/stdio) over an in-memory knowledge base of Brazilian soccer data; pure-stdlib data + query layers, `mcp` SDK only for the server.
- **Structure:** 3 source modules + 1 test module (4 `.py` files, ~2000 LOC); data layer and query engine have zero third-party deps.
- **Interfaces:** 16 MCP tools (no HTTP), backed by `SoccerQueryEngine`; loads 6 provided CSVs.
- **Notable:** Strong team-name normalization (ambiguous Atléticos kept distinct, full-name aliases, accent/suffix stripping); standings computed from results; 39 test functions anchored to real historical facts (e.g. 2019 Flamengo 90 pts); 0 skipped tests; test_coverage=0.92.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
