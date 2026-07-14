# Run Summary: brazilian-soccer-mcp-server (python / sonnet / prompt=neutral · rep3)

## Surface

An MCP server exposing natural-language-style query tools over Brazilian soccer
datasets (Brasileirão, Copa do Brasil, Libertadores, an extended stats file,
a 2003–2019 historical file, and the FIFA player database). The server answers
match, team, player, competition-standings, and statistical-analysis queries.

## Architecture

Clean three-layer separation:

1. **`data_loader.py`** — IO + normalization layer. Lazily reads the 6 CSVs into
   pandas DataFrames, normalizes team names (alias table + suffix stripping) and
   multiple date formats, and exposes a deduplicated `all_matches` union plus a
   module-level singleton (`get_data()`).
2. **`query_tools.py`** — pure query/aggregation functions taking an optional
   injectable `data` argument (which the tests use as a fixture). No MCP coupling.
3. **`server.py`** — thin MCP adapter: 9 `@mcp.tool()` wrappers that translate
   MCP-friendly defaults (empty strings, `0`) into the query layer's `None`s.

The `data` dependency-injection seam is the standout design choice — it lets the
52-test suite run the real query logic against the real datasets without the MCP
transport, which is why tests both exist and pass.

## See also

- `modules.md` — file-level map
- `interfaces.md` — tool + library API
- `../evaluation.md` — full evaluation
- `../findings.jsonl` — structured findings
