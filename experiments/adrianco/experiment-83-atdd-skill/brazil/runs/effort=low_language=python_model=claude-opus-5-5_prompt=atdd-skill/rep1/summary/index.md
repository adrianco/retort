# Architecture summary — Brazilian Soccer MCP server

*(the `run-summary` skill was not invocable in this environment; this is a hand-written
equivalent at the same altitude.)*

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 310 | MCP server. Instantiates `MCPServer("brazilian-soccer")` and registers ~19 `@mcp.tool()` query handlers (match/team/player/competition/stats). Pure formatting + delegation to `SoccerData`. |
| `soccer_data.py` | 375 | Data layer. Loads/merges the six Kaggle CSVs from `data/kaggle/`, normalises team names (accent-stripping, state-suffix, alias + derby tables), and implements all query/aggregation logic (`find_matches`, `find_players`, `record`, `table`, `season_matches`). |
| `tests/acceptance/test_brazilian_soccer_questions.py` | 183 | 32 executable specifications in problem-domain language (`test_should_…`). |
| `tests/acceptance/dsl.py` | 107 | DSL layer — domain verbs (`ask_for_matches`, `confirm_champion`) with defaults. |
| `tests/acceptance/mcp_driver.py` | 83 | Protocol driver — the only layer that knows the SUT is an MCP server; calls tools over an in-memory `Client` transport and holds all assertions/regexes. |
| `tests/acceptance/conftest.py` | 9 | `soccer` fixture wiring DSL → driver. |

## Flow

Spec → `SoccerDsl` (domain verb) → `McpProtocolDriver.ask()` (in-memory MCP `Client` →
`server.mcp` tool) → `SoccerData` query → formatted text answer → `confirm_*` assertion in
the driver.

## Notable design

- **Textbook four-layer ATDD separation** (test / DSL / protocol-driver / SUT), each layer
  at its own abstraction; assertions confined to the protocol driver.
- Team-name normalisation is the heart of the data layer: accent-stripping, state-suffix
  handling, an `AMBIGUOUS` + `ALIASES` table, and a traditional-derby lookup.
- Standings/records are **computed** from match rows (3-1-0 points), not hardcoded.
