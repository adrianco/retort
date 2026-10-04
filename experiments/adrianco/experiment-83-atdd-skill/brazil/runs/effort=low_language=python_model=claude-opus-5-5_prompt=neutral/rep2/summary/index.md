# Run Summary — Brazilian Soccer MCP Server

## Surface

The code implements an MCP (Model Context Protocol) server over stdio that answers
natural-language-style queries about Brazilian soccer, backed by the six provided Kaggle
CSVs (match data from Brasileirão, Copa do Brasil, Libertadores, an extended statistics
file, a historical 2003–2019 file, and the FIFA player database). It exposes 19 tools
covering match search, team records, head-to-head, league standings/champions/relegation,
aggregate statistics, derbies, cross-season comparison, a Libertadores knockout bracket,
and player search/filtering.

## Architecture

- **`soccer.py`** is a standard-library-only knowledge base. A singleton `KB` loads all
  CSVs once (`KB.get()`), parses each row into a `Match` dataclass, and builds a canonical
  team-name map by majority vote across files. Team-name normalization (`normalize_team`)
  handles state suffixes (`Palmeiras-SP` → `palmeiras`), accents, and ~60 aliases/nicknames.
  Query functions are pure, return human-readable text, and share helpers
  (`_record`, `_filtered`, `compute_standings`, `all_matches`, `league_matches`).
- **`server.py`** is a thin JSON-RPC layer. `TOOLS` maps each tool name to
  `(fn, description, inputSchema)`; `handle()` implements `initialize`, `ping`,
  `tools/list`, and `tools/call`, reporting tool errors in-band (`isError`) per the MCP spec.
  `main()` reads newline-delimited JSON from stdin and writes responses to stdout.
- **`test_soccer.py`** exercises normalization, data loading (exact row counts), UTF-8 name
  preservation, 25 sample questions, the MCP protocol via `server.handle`, and one true
  end-to-end test spawning `server.py` as a subprocess over stdio.

## Flow

stdin JSON-RPC → `handle()` → `call_tool()` (arg-schema filtering) → `soccer.*` query
function → formatted text → `tools/call` result content → stdout.

See `modules.md` for the module table.
