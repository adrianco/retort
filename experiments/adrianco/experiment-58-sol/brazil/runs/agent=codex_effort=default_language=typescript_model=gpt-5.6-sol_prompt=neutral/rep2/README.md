# Brazilian Soccer MCP Server

A local [Model Context Protocol](https://modelcontextprotocol.io/) server for natural-language exploration of the six Brazilian soccer datasets in `data/kaggle/`. It loads the CSV files into an in-memory knowledge graph, normalizes team identities across sources, removes overlapping match records, and exposes formatted plus structured results to MCP clients.

## Capabilities

- Search matches by team, opponent, competition, season, date range, stage, and venue.
- Calculate team records, head-to-head comparisons, standings, goal averages, home-win rates, and biggest wins.
- Search all 18,207 FIFA players by name, nationality, club, position group, and rating.
- Traverse cross-file relationships with team profiles (competitions, results, and matching FIFA club players).
- Answer common natural-language questions through `ask_soccer` without an external API key.
- Return UTF-8 display names while matching accent-insensitively (`São Paulo` / `Sao Paulo`) and resolving common full-name/state-suffix variants.

The server uses the stable v1 `@modelcontextprotocol/sdk` API and stdio transport, which is appropriate for local MCP hosts.

## Install and run

Requirements: Node.js 20 or newer.

```bash
npm install
npm run build
npm test
npm start
```

`npm start` speaks MCP JSON-RPC on stdout. Diagnostics go to stderr so they do not corrupt the protocol stream.

To run directly during development:

```bash
npm run dev
```

Set `SOCCER_DATA_DIR` to use another directory containing the same six filenames. Otherwise the server discovers `data/kaggle` from the working directory or installed package.

## MCP client configuration

Add the built server to an MCP host, replacing the path with this repository's absolute path:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/brazilian-soccer-mcp/dist/src/index.js"],
      "env": {
        "SOCCER_DATA_DIR": "/absolute/path/to/brazilian-soccer-mcp/data/kaggle"
      }
    }
  }
}
```

## Tools

| Tool | Purpose |
|---|---|
| `ask_soccer` | Route a natural-language soccer question |
| `search_matches` | Filter match history across all five match files |
| `get_head_to_head` | Compare two teams and list meetings |
| `get_team_statistics` | Calculate W/D/L, goals, points, and win rate |
| `get_team_profile` | Combine match/competition and FIFA club relationships |
| `search_players` | Search and rank FIFA player records |
| `get_standings` | Reconstruct a season table from results |
| `get_competition_statistics` | Aggregate goals, outcomes, and biggest wins |
| `get_derbies` | Find traditional-rival matchups |
| `get_dataset_summary` | Report loaded graph and source coverage |

Example questions:

- `Show me all Flamengo vs Fluminense matches`
- `What is Corinthians' home record in 2022?`
- `Who won the 2019 Brasileirão?`
- `Who are the top Brazilian players?`
- `Which team scored the most goals in Serie A 2023?`
- `Show me all derbies in 2023`

## Design

The implementation has four layers:

1. `data-loader.ts` parses all six CSV schemas into common match/player domain types.
2. `knowledge-base.ts` builds team, competition, and club-player graph indexes and deduplicates overlapping sources.
3. `soccer-service.ts` performs deterministic searches and aggregations; `query-router.ts` maps common Portuguese/English question shapes onto those operations.
4. `mcp-server.ts` exposes the operations through the official MCP SDK; `index.ts` provides the stdio executable.

For standings, the dedicated competition file is preferred over overlapping extended/historical files. Ranking uses points, wins, goal difference, goals scored, then team name. Results are explicitly calculations from the supplied data, not claims about rules outside it.

## Data limitations

- The files contain final team scores but no player goal events, so top scorers cannot be inferred reliably. The server returns an explicit limitation instead of inventing an answer.
- Some supplied seasons are incomplete or contain `NA` scores. Unplayed/invalid rows are skipped and statistics describe only matches with final scores.
- The FIFA file is a historical snapshot and does not contain every Brazilian club/player relationship. A valid search may therefore return zero players.
- Relegation responses are table-derived bottom positions; administrative decisions and season-specific relegation rules are not encoded.

## Tests

```bash
npm run check
```

The suite covers normalization, all six real datasets, head-to-head queries, records, the known 2019 table, player attributes, cross-file profiles, 20 natural-language questions, limitations, and an in-memory MCP client/server protocol round trip.

## Data attribution

The included data and licenses are documented in [TASK.md](TASK.md) and `brazilian-soccer-mcp-guide.md`: three match datasets and the historical Brasileirão data are CC BY 4.0, the extended match dataset is CC0, and the FIFA player dataset is Apache 2.0.
