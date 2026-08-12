# Brazilian Soccer MCP Server

Run the dependency-free MCP server with:

```bash
python soccer_mcp.py
```

It reads newline-delimited JSON-RPC requests from stdin and writes MCP responses
to stdout. The `SoccerDatabase` class is also a regular Python API for scripts
and tests. It loads all six supplied CSV datasets, normalizes accents and team
state suffixes, supports match/player/team/head-to-head/standings/statistics
queries, and includes a small deterministic natural-language router for clients
that do not provide their own LLM.

Run tests with `python -m unittest -v`.
